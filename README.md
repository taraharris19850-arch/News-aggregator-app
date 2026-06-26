# 新闻播音训练

每天从 **人民网 / 新华网 / 人民日报(电子版)** 抓取热点新闻,自动加工成
**播音主持考试训练材料**,在手机上(尤其 iPhone)随时打开练习。

每条新闻都包含:

- 📰 **新闻播报稿** —— 标题 + 分段正文,适合朗读
- 🔤 **难点字词正音** —— 自动标注多音字、易错词,带语境读音(可在正文上方显示拼音)
- 🎤 **即兴评述话题** —— 由标题提炼的 3 个评述角度
- 🤖 **AI 评述范例** —— 配置 API Key 后,用 Claude 自动生成即兴评述示范稿
- ⏱ **计时朗读** —— 读完后给出真实语速(字/分)并评价快慢(播音新闻标准 240–300 字/分)
- 🎙 **录音对比** —— 手机端录下自己的朗读,回放自检(需 HTTPS,云端部署后可用)
- ⭐ **收藏与历史** —— 收藏喜欢的稿子,按日期查看往日存档(保留最近 30 天)
- 🔎 **分类与搜索** —— 按 时政/经济/民生/文化/国际/科技 分类,标题正文全文搜索

---

## 目录结构

```
新闻播音训练/
├── scraper.py                 抓取 + 加工脚本(核心,含分类与 AI 评述)
├── run_daily.sh               每日运行入口(供定时任务调用,带日志)
├── serve.sh                   一键启动本地网页服务器
├── requirements.txt           Python 依赖
├── com.heping.newsbroadcast.plist   macOS 每天9点定时任务模板
├── .github/workflows/daily.yml      GitHub Actions:每天9点云端抓取+发布
├── logs/                       运行日志
└── web/                        手机端网页 App
    ├── index.html / style.css / app.js
    ├── manifest.webmanifest / sw.js / icon*.png
    └── data/                   抓取结果(latest.json = 手机端读取的最新数据)
```

---

## 快速开始(三步)

### 1. 安装依赖(只需一次)

```bash
cd "新闻播音训练"
python3 -m pip install -r requirements.txt
```

### 2. 抓取今天的新闻

```bash
python3 scraper.py
```

成功后会在 `web/data/` 生成当天数据。

### 3. 在手机上看

```bash
./serve.sh
```

终端会显示两个地址,例如:

```
本机访问:   http://localhost:8000
手机访问:   http://192.168.x.x:8000   (手机与电脑连同一 WiFi)
```

**手机与这台 Mac 连同一个 WiFi**,用 Safari 打开「手机访问」那个地址即可。

---

## 加到 iPhone 主屏,当成 App 用

1. iPhone 用 **Safari** 打开上面的「手机访问」地址
2. 点底部「分享」按钮 → **添加到主屏幕**
3. 主屏会出现红色「播」图标,点开即全屏运行,和 App 一样

> 离线也能看上一次加载过的内容(已做离线缓存)。

---

## ☁️ 云端部署(推荐:随时随地、不依赖电脑开机)

部署到 GitHub 后:**每天北京时间 9:00 自动抓取**,生成网页托管在 GitHub Pages,
手机随时随地打开即可(也能加到 iOS 主屏)。录音功能也只有在这种 HTTPS 环境下才可用。

项目已内置好自动化(`.github/workflows/daily.yml`),你只需做一次性配置:

### 1. 注册 / 登录 GitHub
打开 <https://github.com>,注册一个免费账号(已有可跳过)。

### 2. 新建一个空仓库
点右上角 **+ → New repository**,名字如 `news-broadcast`,选 **Public**(公开,Pages 免费),
**不要**勾选任何初始化选项(README/.gitignore 都不要),点 Create。

### 3. 把本项目推上去
在终端进入项目目录,执行(把 `你的用户名` 和仓库名换成你的):

```bash
cd "/Users/taraharris/Dropbox/Mac/Documents/Claude/Projects/Claduepot Studio folder/新闻播音训练"
git remote add origin https://github.com/你的用户名/news-broadcast.git
git push -u origin main
```

### 4. 打开 GitHub Pages
仓库页面 → **Settings → Pages → Build and deployment → Source** 选 **GitHub Actions**。

### 5.(可选)开启 AI 评述范例
仓库 → **Settings → Secrets and variables → Actions → New repository secret**,
名字填 `ANTHROPIC_API_KEY`,值填你的 Claude API Key(在 <https://console.anthropic.com> 获取)。
不配也行——其它功能照常,只是没有 AI 范例。

### 6. 立即跑一次(不必等到明早 9 点)
仓库 → **Actions → 每日抓取并发布 → Run workflow**。
跑完后,网址就是:

```
https://你的用户名.github.io/news-broadcast/
```

手机 Safari 打开它 →「分享」→「添加到主屏幕」,就是一个随时随地可用的 App。

> 备注:
> - 工作流已在文件里声明了 `contents: write` 权限,能把每天的数据提交回仓库累积历史。
>   若第 6 步推送数据报权限错误,到 **Settings → Actions → General → Workflow permissions**
>   选 **Read and write permissions** 即可。
> - 国内访问 GitHub Pages 有时较慢,手机连梯子更稳。
> - AI 评述每天约 18 条,用量很小;费用见 Anthropic 控制台。

---

## 让它每天早上 9 点自动抓取(macOS · 本地方式)

项目自带 launchd 定时任务模板。安装:

```bash
# 1. 链接到 LaunchAgents 目录
ln -sf "/Users/taraharris/Dropbox/Mac/Documents/Claude/Projects/Claduepot Studio folder/新闻播音训练/com.heping.newsbroadcast.plist" ~/Library/LaunchAgents/

# 2. 加载任务
launchctl load ~/Library/LaunchAgents/com.heping.newsbroadcast.plist

# 立即测试运行一次(不必等到9点)
launchctl start com.heping.newsbroadcast
```

抓取日志见 `logs/run.log`。

停用 / 卸载:

```bash
launchctl unload ~/Library/LaunchAgents/com.heping.newsbroadcast.plist
```

> ⚠️ launchd 要求到点时电脑处于**开机/唤醒**状态。若 9 点电脑在睡眠,任务会在下次唤醒后补跑。
> 想做到「手机随时随地都能刷到最新、且不依赖电脑开机」,需要把它部署到云端
> (例如 GitHub Actions 每天定时抓取 + GitHub Pages 托管网页)。需要的话可以再帮你接上。

---

## 训练功能怎么用

进入任意一条新闻后:

- **A- / A+**:调正文字号
- **注音**:开关,在难点字/词上方显示拼音,用于正音
- **开始朗读 → 读完计速**:开始读时点「开始朗读」,读完整篇点「读完计速」,
  会算出你的实际语速并提示偏快 / 标准 / 偏慢
- **难点字词 · 正音**:本篇检出的多音字、易错词及规范读音
- **即兴评述 · 话题角度**:可直接当作即兴评述 / 新闻评论练习题

---

## 可调参数(在 `scraper.py` 顶部)

| 变量 | 含义 | 默认 |
|------|------|------|
| `PER_SOURCE` | 每个来源抓取条数 | 6 |
| `READ_CPM` | 朗读语速基准(字/分,用于预估目标时长) | 260 |
| `KEEP_DAYS` | 历史存档保留天数 | 30 |
| `AI_MODEL` | 生成 AI 评述的模型(环境变量) | claude-opus-4-8 |
| `YICUO` | 播音易错词 → 规范读音表(可自行增补) | 约 50 词 |
| `HETERONYM` | 需要标注的多音字集合(可自行增补) | 约 60 字 |

---

## 说明

- 内容来源于人民网、新华网、人民日报官网,**版权归原网站**;本工具仅供个人学习
  与播音练习使用,请勿用于商业传播或二次发布。
- 若某天某个来源改版导致抓取为空,脚本会自动跳过该来源并在日志中记录,不影响其它来源。
