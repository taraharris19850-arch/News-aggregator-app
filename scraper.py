#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
新闻播音训练 · 抓取与加工脚本
-------------------------------------------------
每天抓取 人民网 / 新华网 / 人民日报(电子版) 的热点新闻,
加工成「播音主持考试」训练材料:
  1) 新闻播报稿(标题 + 分段正文)
  2) 难点字词注音(多音字 + 易错词,带语境读音)
  3) 即兴评述话题(由标题提炼角度)
  4) 计时朗读所需的字数 / 预计时长

输出:
  web/data/news_YYYY-MM-DD.json   (当天存档)
  web/data/latest.json            (手机端读取的最新数据)
  web/data/index.json             (历史日期索引)

依赖: requests, beautifulsoup4, lxml, pypinyin
"""

import os, re, json, time, datetime, traceback
from urllib.parse import urljoin
import requests
from bs4 import BeautifulSoup
from pypinyin import pinyin, Style

# ----------------------------------------------------------------------------
HERE = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(HERE, "web", "data")
os.makedirs(DATA_DIR, exist_ok=True)

HEADERS = {
    "User-Agent": ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                   "AppleWebKit/605.1.15 (KHTML, like Gecko) "
                   "Version/17.0 Safari/605.1.15"),
    "Accept-Language": "zh-CN,zh;q=0.9",
}

PER_SOURCE = 5          # 每个来源抓取条数(只算「有导语」的合格文章)
REQ_TIMEOUT = 15
READ_CPM = 260          # 播音平均语速:字/分钟(用于预估朗读时长)
KEEP_DAYS = 30          # 历史存档保留天数
MIN_CHARS = 300         # 正文最少字数(短讯/图说不作训练材料)

# 「有导语」判定:正经消息类新闻,开头带电头/记者/时间地点等导语标志。
# 用来过滤掉评论、短讯、图片特写、新媒体产品等没有新闻导语的稿件。
LEAD_MARKERS = re.compile(
    r"新华社[^。,，、]{0,12}电"           # 新华社北京6月25日电
    r"|本报[^。,，、]{0,12}(电|讯)"        # 本报北京电 / 本报讯
    r"|中新社[^。,，、]{0,12}电"
    r"|人民网[^。,，、]{0,12}电"
    r"|[（(]记者[^）)]{0,24}[）)]"        # (记者XXX)
    r"|记者从[^。]{1,24}(获悉|了解到|获知)"
    r"|据[^。]{1,18}(报道|消息|获悉|通报)"
    r"|\d{1,2}月\d{1,2}日[^。]{0,14}(电|讯|报道|获悉|召开|举行|发布)"
)


def has_lead(paragraphs):
    """看正文开头(前两段/前 160 字)是否具备新闻导语标志。"""
    head = "".join(paragraphs[:2])[:160]
    return bool(LEAD_MARKERS.search(head))

# ----------------------------------------------------------------------------
# 播音主持「易错词」语境读音表(整词命中,直接给规范读音)
YICUO = {
    "档案": "dàng àn", "强劲": "qiáng jìng", "押解": "yā jiè", "分外": "fèn wài",
    "倔强": "jué jiàng", "包扎": "bāo zā", "处理": "chǔ lǐ", "处罚": "chǔ fá",
    "殷红": "yān hóng", "角色": "jué sè", "模样": "mú yàng", "复辟": "fù bì",
    "给予": "jǐ yǔ", "提防": "dī fáng", "标识": "biāo zhì", "卓越": "zhuó yuè",
    "包庇": "bāo bì", "处于": "chǔ yú", "着重": "zhuó zhòng",
    "刹那": "chà nà", "刹车": "shā chē", "纤维": "xiān wéi", "纤细": "xiān xì",
    "亟待": "jí dài", "脚踏实地": "jiǎo tà shí dì",
    "供给": "gōng jǐ", "供应": "gōng yìng", "屏蔽": "píng bì", "差错": "chā cuò",
    "调研": "diào yán", "调动": "diào dòng", "重创": "zhòng chuāng",
    "创伤": "chuāng shāng", "胆怯": "dǎn qiè", "果实累累": "guǒ shí léi léi",
    "削减": "xuē jiǎn", "勉强": "miǎn qiǎng", "符合": "fú hé", "粗犷": "cū guǎng",
    "档次": "dàng cì", "横财": "hèng cái", "蛮横": "mán hèng", "应运而生": "yìng yùn ér shēng",
    "处置": "chǔ zhì", "勘察": "kān chá", "炽热": "chì rè", "氛围": "fēn wéi",
    "缜密": "zhěn mì", "教诲": "jiào huì", "湖泊": "hú pō", "停泊": "tíng bó",
    "估量": "gū liang", "胜券在握": "shèng quàn zài wò", "卷帙浩繁": "juàn zhì hào fán",
}
# 表里偶有占位脏键,清掉空值
YICUO = {k: v for k, v in YICUO.items() if v and "一" <= k[0] <= "鿿"}

# 值得为播音标注的「多音字」(语境读音由 pypinyin 现场判定)
HETERONYM = set("处长重率系还都为和与应强差调创据担当给卷几济假将角教解卡看落"
                "蒙模难宁朴曲散扇舍盛数缩提血兴削行载占朝称乘分便藏宿"
                "颤泊间空漂晕咽")
HETERONYM = {c for c in HETERONYM if "一" <= c <= "鿿"}

# ----------------------------------------------------------------------------
def fetch(url):
    r = requests.get(url, headers=HEADERS, timeout=REQ_TIMEOUT)
    r.raise_for_status()
    enc = r.apparent_encoding or "utf-8"
    if enc.lower() in ("gb2312", "gbk"):
        enc = "gb18030"
    r.encoding = enc
    return r.text


def clean(txt):
    txt = re.sub(r"\s+", " ", txt or "").strip()
    return txt


def extract_body(soup):
    """按已知选择器取正文,失败则回退到 <p> 最多的容器。"""
    for sel in (".rm_txt_con", "#detail", "#detailContent", "#ozoom",
                ".show_text", "#rwb_zw", ".article", "founder-content"):
        el = soup.select_one(sel)
        if el:
            ps = [clean(p.get_text()) for p in el.find_all("p")]
            ps = [p for p in ps if len(p) >= 8]
            if ps:
                return ps
    # 回退:全页面里 <p> 文本量最大的块
    best, best_len = None, 0
    for div in soup.find_all(["div", "section", "article"]):
        ps = [clean(p.get_text()) for p in div.find_all("p")]
        ps = [p for p in ps if len(p) >= 8]
        total = sum(len(p) for p in ps)
        if total > best_len:
            best, best_len = ps, total
    return best or []


# ----------------------------------------------------------------------------
# 各来源:返回 [(title, url), ...]
def list_people():
    html = fetch("http://www.people.com.cn/")
    soup = BeautifulSoup(html, "lxml")
    out, seen = [], set()
    for a in soup.find_all("a", href=True):
        t = clean(a.get_text())
        h = a["href"]
        if len(t) < 12:
            continue
        if not re.search(r"/n\d?/\d{4}/\d{4}/.*c\d+-\d+\.html", h):
            continue
        h = urljoin("http://www.people.com.cn/", h)
        if h in seen:
            continue
        seen.add(h)
        out.append((t, h))
    return out


def list_xinhua():
    html = fetch("http://www.news.cn/")
    soup = BeautifulSoup(html, "lxml")
    out, seen = [], set()
    for a in soup.find_all("a", href=True):
        t = clean(a.get_text())
        h = a["href"]
        if len(t) < 12:
            continue
        if "/2026" not in h and "/2025" not in h:
            continue
        if not h.rstrip("/").endswith("c.html"):
            continue
        if h.startswith("//"):
            h = "https:" + h
        h = urljoin("http://www.news.cn/", h)
        if h in seen:
            continue
        seen.add(h)
        out.append((t, h))
    return out


def list_rmrb():
    """人民日报电子版 · 要闻版(node_01)"""
    today = datetime.date.today()
    base = ("http://paper.people.com.cn/rmrb/pc/layout/"
            f"{today:%Y%m}/{today:%d}/node_01.html")
    try:
        html = fetch(base)
    except Exception:
        return []
    soup = BeautifulSoup(html, "lxml")
    out, seen = [], set()
    for a in soup.find_all("a", href=True):
        t = clean(a.get_text())
        h = a["href"]
        if len(t) < 10 or "content" not in h:
            continue
        h = urljoin(base, h)
        if h in seen:
            continue
        seen.add(h)
        out.append((t, h))
    return out


SOURCES = [
    ("人民网", list_people),
    ("新华网", list_xinhua),
    ("人民日报", list_rmrb),
]

# ----------------------------------------------------------------------------
def annotate(paragraphs):
    """返回 (难点字词列表, 带注音的段落HTML列表)。"""
    full = "".join(paragraphs)
    hard, seen = [], set()

    # 1) 易错整词
    for word, py in YICUO.items():
        if word in full and word not in seen:
            seen.add(word)
            hard.append({"word": word, "pinyin": py, "note": "易错词"})

    # 2) 多音字(取段落语境中的实际读音)
    #    仅对「连续汉字片段」调用 pypinyin —— 纯汉字输入保证逐字一一对齐,
    #    避免数字/英文被合并成一项导致错位。
    for para in paragraphs:
        for run in re.findall(r"[一-鿿]+", para):
            rds = pinyin(run, style=Style.TONE, heteronym=False)
            for ch, rd in zip(run, rds):
                if ch in HETERONYM and ch not in seen:
                    seen.add(ch)
                    hard.append({"word": ch, "pinyin": rd[0], "note": "多音字"})

    hard = hard[:14]

    # 3) 生成 ruby 注音段落:长词优先,用占位符防止嵌套/二次匹配
    targets = sorted({h["word"]: h["pinyin"] for h in hard}.items(),
                     key=lambda kv: -len(kv[0]))
    ruby_paras = []
    for para in paragraphs:
        safe = (para.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))
        tokens = {}
        for i, (word, py) in enumerate(targets):
            if not word:
                continue
            tok = chr(0xE000 + i)   # 私有区哨兵字符,绝不会撞上正文内容
            if word in safe:
                safe = safe.replace(word, tok)
                tokens[tok] = f'<ruby>{word}<rt>{py}</rt></ruby>'
        for tok, ruby in tokens.items():
            safe = safe.replace(tok, ruby)
        ruby_paras.append(safe)
    return hard, ruby_paras


def make_topics(title):
    """由标题提炼即兴评述话题与角度。"""
    core = re.sub(r"[｜|·—\-—\[\]【】（）()]", " ", title).strip()
    kw = core.split()[0] if core.split() else core
    return [
        f"【新闻概述】用 30 秒清晰复述这则新闻的核心事实:谁、何时、何地、做了什么、结果如何。",
        f"【观点评述】围绕「{core}」,谈谈它反映了什么趋势或问题,你的看法和理由是什么?",
        f"【联系实际】结合社会现实或自身经历,谈谈「{kw}」对青年/行业/社会的启示。",
    ]


# ----------------------------------------------------------------------------
# 新闻分类:先看 URL 频道,再看标题关键词,最后兜底「时政」
CATEGORIES = ["时政", "经济", "民生", "社会", "文化", "国际", "科技"]
_CAT_URL = [
    ("国际", ("/world", "/world.cn", "world.people", "/mil", "/military")),
    ("经济", ("/finance", "finance.people", "/money", "/fortune", "/economy", "/industry", "/house", "/auto")),
    ("科技", ("/tech", "/science", "/it/", "kj.", "/digital")),
    ("文化", ("/culture", "culture.people", "/ent", "ent.people", "/book", "/art", "/edu", "edu.people", "/sports", "sports.people")),
    ("社会", ("/society", "society.people", "/legal", "/social")),
    ("民生", ("/health", "health.people", "/food", "/env", "/民生")),
]
_CAT_KW = {
    "国际": ("外交", "国际", "全球", "联合国", "海外", "外长", "总统", "达沃斯", "进出口", "一带一路"),
    "经济": ("经济", "金融", "市场", "消费", "产业", "粮食", "丰收", "就业", "财政", "投资", "企业", "GDP", "贸易"),
    "科技": ("科技", "创新", "人工智能", "数字", "芯片", "航天", "卫星", "量子"),
    "文化": ("文化", "文艺", "教育", "考试", "非遗", "博物馆", "电影", "体育", "奥运"),
    "社会": ("社会", "法治", "案件", "公益", "志愿", "安全生产"),
    "民生": ("民生", "医疗", "健康", "养老", "住房", "社保", "环保", "生态", "饭碗"),
    "时政": ("习近平", "总书记", "中央", "政治局", "国务院", "李强", "全国政协", "人大", "党建", "代表"),
}


def classify(title, url):
    u = (url or "").lower()
    for cat, keys in _CAT_URL:
        if any(k in u for k in keys):
            return cat
    for cat in ("时政", "经济", "民生", "社会", "文化", "国际", "科技"):
        if any(k in title for k in _CAT_KW.get(cat, ())):
            return cat
    return "时政"


# ----------------------------------------------------------------------------
# 可选:用 Claude 为每条新闻生成「即兴评述范例」(需要 ANTHROPIC_API_KEY)
AI_MODEL = os.environ.get("AI_MODEL", "claude-opus-4-8")
_AI_SYS = (
    "你是资深播音主持教师,为艺考生撰写「即兴评述」示范稿。"
    "根据给定新闻,写一篇 280–360 字的即兴评述范文,要求:"
    "1) 结构清晰(亮明观点—分析论证—联系现实—收束升华);"
    "2) 口语化、有逻辑、有思辨,适合考场口头表达;"
    "3) 立场积极正向,符合主流价值导向;"
    "4) 只输出范文正文本身,不要标题、不要任何解释或前后缀。"
)


def gen_commentary(client, title, body):
    """调用 Claude 生成一条即兴评述范例,失败返回空串。"""
    try:
        msg = client.messages.create(
            model=AI_MODEL,
            max_tokens=1200,
            output_config={"effort": "low"},
            system=_AI_SYS,
            messages=[{"role": "user",
                       "content": f"新闻标题:{title}\n\n新闻正文(节选):{body[:1200]}"}],
        )
        parts = [b.text for b in msg.content if getattr(b, "type", "") == "text"]
        return "".join(parts).strip()
    except Exception as e:
        print(f"    · AI评述失败:{e}")
        return ""


def build_item(source, title, url):
    html = fetch(url)
    soup = BeautifulSoup(html, "lxml")
    paragraphs = extract_body(soup)
    if not paragraphs:
        return None
    text = "".join(paragraphs)
    char_count = len(re.sub(r"[\s\W]", "", text))
    # 只保留「有导语」的合格消息:字数达标 + 开头具备导语标志
    if char_count < MIN_CHARS or not has_lead(paragraphs):
        return None
    hard, ruby = annotate(paragraphs)
    return {
        "source": source,
        "title": clean(title),
        "url": url,
        "category": classify(clean(title), url),
        "paragraphs": paragraphs,
        "paragraphs_ruby": ruby,
        "hard_words": hard,
        "topics": make_topics(clean(title)),
        "ai_commentary": "",
        "char_count": char_count,
        "read_seconds": round(char_count / READ_CPM * 60),
    }


def main():
    items, idx = [], 0
    for source, lister in SOURCES:
        try:
            links = lister()
        except Exception as e:
            print(f"[{source}] 列表抓取失败: {e}")
            continue
        print(f"[{source}] 候选 {len(links)} 条")
        n = 0
        for title, url in links:
            if n >= PER_SOURCE:
                break
            try:
                it = build_item(source, title, url)
                if it:
                    idx += 1
                    it["id"] = idx
                    items.append(it)
                    n += 1
                    print(f"  ✓ {it['title'][:30]} ({it['char_count']}字)")
                time.sleep(0.5)
            except Exception as e:
                print(f"  ✗ {title[:24]}: {e}")

    # 可选:批量生成 AI 即兴评述范例(仅当配置了 ANTHROPIC_API_KEY)
    if os.environ.get("ANTHROPIC_API_KEY"):
        try:
            import anthropic
            client = anthropic.Anthropic()
            print(f"\n[AI] 生成即兴评述范例(模型 {AI_MODEL})…")
            for it in items:
                it["ai_commentary"] = gen_commentary(
                    client, it["title"], "".join(it["paragraphs"]))
                if it["ai_commentary"]:
                    print(f"  ✓ {it['title'][:24]}")
        except Exception as e:
            print(f"[AI] 跳过(初始化失败):{e}")
    else:
        print("\n[AI] 未配置 ANTHROPIC_API_KEY,跳过即兴评述范例生成")

    today = datetime.date.today().isoformat()
    cats = sorted({it["category"] for it in items}, key=CATEGORIES.index)
    payload = {
        "date": today,
        "generated_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "count": len(items),
        "sources": [s for s, _ in SOURCES],
        "categories": cats,
        "items": items,
    }
    day_file = os.path.join(DATA_DIR, f"news_{today}.json")
    with open(day_file, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    with open(os.path.join(DATA_DIR, "latest.json"), "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

    # 只保留最近 KEEP_DAYS 天的存档,避免仓库无限膨胀
    dates = sorted({fn[5:-5] for fn in os.listdir(DATA_DIR)
                    if fn.startswith("news_") and fn.endswith(".json")}, reverse=True)
    for old in dates[KEEP_DAYS:]:
        os.remove(os.path.join(DATA_DIR, f"news_{old}.json"))
    dates = dates[:KEEP_DAYS]

    # 维护历史索引
    with open(os.path.join(DATA_DIR, "index.json"), "w", encoding="utf-8") as f:
        json.dump({"dates": dates}, f, ensure_ascii=False, indent=2)
    print(f"\n完成:{len(items)} 条 → {day_file}")


if __name__ == "__main__":
    try:
        main()
    except Exception:
        traceback.print_exc()
