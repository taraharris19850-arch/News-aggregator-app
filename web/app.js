'use strict';

let DATA = null;
let curCat = '全部';        // 分类筛选
let curSource = '全部';     // 来源筛选
let favOnly = false;        // 只看收藏
let query = '';             // 搜索词
let curItem = null;

let timer = { id:null, sec:0, running:false };
let rec = { mr:null, chunks:[], url:null, recording:false };

const $ = (s) => document.querySelector(s);

// ---------- 收藏(localStorage) ----------
const FAV_KEY = 'bc_favs';
function loadFavs(){ try { return new Set(JSON.parse(localStorage.getItem(FAV_KEY) || '[]')); } catch { return new Set(); } }
function saveFavs(set){ localStorage.setItem(FAV_KEY, JSON.stringify([...set])); }
let favs = loadFavs();
const isFav = (it) => favs.has(it.url);
function toggleFav(it){
  if (favs.has(it.url)) favs.delete(it.url); else favs.add(it.url);
  saveFavs(favs);
}

// ---------- 加载数据 ----------
async function fetchJSON(path){
  const res = await fetch(path, { cache:'no-store' });
  if (!res.ok) throw new Error(res.status);
  return res.json();
}

async function loadDate(file){
  try {
    DATA = await fetchJSON('data/' + file);
  } catch (e) {
    $('#meta').textContent = '该日期暂无数据';
    $('#list').innerHTML = '<div class="empty">没有这一天的数据。</div>';
    return;
  }
  $('#meta').textContent = `${DATA.date} · 共 ${DATA.count} 条 · 更新于 ${(''+DATA.generated_at).slice(11,16)}`;
  buildFilters();
  render();
}

async function init(){
  // 历史日期下拉
  let dates = [];
  try { dates = (await fetchJSON('data/index.json')).dates || []; } catch {}
  const dateSel = $('#dateSel');
  if (dates.length){
    dateSel.innerHTML = '<option value="latest.json">最新</option>' +
      dates.map(d => `<option value="news_${d}.json">${d}</option>`).join('');
  } else {
    dateSel.innerHTML = '<option value="latest.json">最新</option>';
  }
  dateSel.onchange = () => loadDate(dateSel.value);
  await loadDate('latest.json');
}

// ---------- 筛选条 ----------
function buildFilters(){
  // 来源下拉
  const sourceSel = $('#sourceSel');
  sourceSel.innerHTML = '<option value="全部">全部来源</option>' +
    (DATA.sources || []).map(s => `<option value="${s}">${s}</option>`).join('');
  sourceSel.value = curSource;
  sourceSel.onchange = () => { curSource = sourceSel.value; render(); };

  // 分类 chips：全部 / ⭐收藏 / 各分类
  const cats = DATA.categories && DATA.categories.length ? DATA.categories : [];
  const chips = ['全部', '⭐收藏', ...cats];
  $('#filters').innerHTML = chips.map(c => {
    const active = (c === '⭐收藏') ? favOnly : (!favOnly && c === curCat);
    return `<button class="filter ${active?'active':''}" data-c="${c}">${c}</button>`;
  }).join('');
  document.querySelectorAll('.filter').forEach(b => b.onclick = () => {
    const c = b.dataset.c;
    if (c === '⭐收藏'){ favOnly = !favOnly; }
    else { favOnly = false; curCat = c; }
    buildFilters(); render();
  });
}

function fmtSec(s){
  const m = Math.floor(s/60), r = s%60;
  return String(m).padStart(2,'0') + ':' + String(r).padStart(2,'0');
}

function visibleItems(){
  const q = query.trim();
  return DATA.items.filter(i => {
    if (favOnly && !isFav(i)) return false;
    if (!favOnly && curCat !== '全部' && i.category !== curCat) return false;
    if (curSource !== '全部' && i.source !== curSource) return false;
    if (q){
      const hay = (i.title + ' ' + i.paragraphs.join('')).toLowerCase();
      if (!hay.includes(q.toLowerCase())) return false;
    }
    return true;
  });
}

function render(){
  const items = visibleItems();
  if (!items.length){
    $('#list').innerHTML = '<div class="empty">没有匹配的内容</div>';
    return;
  }
  $('#list').innerHTML = items.map(i => `
    <div class="card" data-id="${i.id}">
      <div class="tagrow">
        <span class="tag">${i.source}</span>
        <span class="tag cat">${i.category||''}</span>
        ${i.ai_commentary ? '<span class="tag ai-badge">AI范例</span>' : ''}
        ${isFav(i) ? '<span class="fav-mark">★</span>' : ''}
      </div>
      <h3>${escapeHtml(i.title)}</h3>
      <div class="stat">
        <span><b>${i.char_count}</b> 字</span>
        <span>约 <b>${fmtSec(i.read_seconds)}</b></span>
        <span><b>${i.hard_words.length}</b> 个难点</span>
      </div>
    </div>`).join('');
  document.querySelectorAll('.card').forEach(c => c.onclick = () => openReader(+c.dataset.id));
}

// ---------- 阅读 / 训练 ----------
function openReader(id){
  curItem = DATA.items.find(i => i.id===id);
  if (!curItem) return;
  const it = curItem;
  $('#rSource').textContent = it.source;
  $('#rCat').textContent = it.category || '';
  $('#rTitle').textContent = it.title;
  $('#rStat').innerHTML = `<span><b>${it.char_count}</b> 字</span><span>目标约 <b>${fmtSec(it.read_seconds)}</b>(按 260 字/分)</span>`;
  $('#rBody').innerHTML = it.paragraphs_ruby.map(p => `<p>${p}</p>`).join('');
  $('#rHard').innerHTML = it.hard_words.length
    ? it.hard_words.map(h => `<div class="hw"><span class="py">${h.pinyin}</span><span class="wd">${h.word}</span><span class="nt">${h.note}</span></div>`).join('')
    : '<div class="empty" style="padding:10px">本篇未检出常见难点字词</div>';
  $('#rTopics').innerHTML = it.topics.map(t => `<li>${escapeHtml(t)}</li>`).join('');
  if (it.ai_commentary){
    $('#aiWrap').classList.remove('hidden');
    $('#rAi').textContent = it.ai_commentary;
  } else {
    $('#aiWrap').classList.add('hidden');
  }
  $('#rLink').href = it.url;
  $('#tTarget').textContent = fmtSec(it.read_seconds);
  updateFavBtn();

  resetTimer();
  resetRec();
  $('#reader').classList.remove('hidden');
  $('.reader-scroll').scrollTop = 0;
  document.body.style.overflow = 'hidden';
}

function closeReader(){
  stopTimer();
  stopRec(true);
  $('#reader').classList.add('hidden');
  document.body.style.overflow = '';
  render();   // 收藏状态可能变化,刷新列表
}

function updateFavBtn(){
  const on = curItem && isFav(curItem);
  $('#favBtn').textContent = on ? '★' : '☆';
  $('#favBtn').classList.toggle('on', !!on);
}

// ---------- 计时朗读 ----------
function tickUI(){ $('#tTime').textContent = fmtSec(timer.sec); }
function startTimer(){
  if (timer.running) return;
  timer.running = true;
  $('#tResult').classList.add('hidden');
  $('#tStart').textContent = '暂停';
  $('#tStart').classList.add('running');
  timer.id = setInterval(() => { timer.sec++; tickUI(); }, 1000);
}
function pauseTimer(){
  timer.running = false; clearInterval(timer.id);
  $('#tStart').textContent = '继续'; $('#tStart').classList.remove('running');
}
function stopTimer(){ timer.running=false; clearInterval(timer.id); }
function resetTimer(){
  stopTimer(); timer.sec=0;
  $('#tStart').textContent='开始朗读'; $('#tStart').classList.remove('running');
  $('#tTime').textContent='00:00';
  $('#tResult').classList.add('hidden');
}
function doneTimer(){
  if (!curItem || timer.sec < 1) return;
  stopTimer();
  $('#tStart').textContent='开始朗读'; $('#tStart').classList.remove('running');
  const cpm = Math.round(curItem.char_count / (timer.sec/60));
  let verdict, cls;
  if (cpm < 240){ verdict='偏慢,可适当提速'; cls='slow'; }
  else if (cpm <= 300){ verdict='语速标准 👍'; cls='good'; }
  else { verdict='偏快,注意吐字清晰'; cls='fast'; }
  const r = $('#tResult');
  r.className = 't-result ' + cls;
  r.innerHTML = `用时 <b>${fmtSec(timer.sec)}</b> · 语速 <b>${cpm}</b> 字/分 · ${verdict}`;
}

// ---------- 录音对比 ----------
function resetRec(){
  stopRec(true);
  if (rec.url){ URL.revokeObjectURL(rec.url); rec.url=null; }
  const a = $('#recAudio'); a.classList.add('hidden'); a.removeAttribute('src');
  $('#recBtn').textContent = '开始录音';
  $('#recBtn').classList.remove('running');
  $('#recHint').textContent = '';
}
function stopRec(silent){
  if (rec.mr && rec.recording){
    try { rec.mr.stop(); } catch {}
  }
  rec.recording = false;
}
async function toggleRec(){
  if (rec.recording){ stopRec(); return; }
  if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia){
    $('#recHint').textContent = '当前环境不支持录音';
    return;
  }
  try {
    const stream = await navigator.mediaDevices.getUserMedia({ audio:true });
    rec.chunks = [];
    rec.mr = new MediaRecorder(stream);
    rec.mr.ondataavailable = e => { if (e.data.size) rec.chunks.push(e.data); };
    rec.mr.onstop = () => {
      stream.getTracks().forEach(t => t.stop());
      if (rec.url) URL.revokeObjectURL(rec.url);
      const blob = new Blob(rec.chunks, { type: rec.mr.mimeType || 'audio/webm' });
      rec.url = URL.createObjectURL(blob);
      const a = $('#recAudio'); a.src = rec.url; a.classList.remove('hidden');
      $('#recBtn').textContent = '重新录音';
      $('#recBtn').classList.remove('running');
      $('#recHint').textContent = '播放回放,对照范读自检';
    };
    rec.mr.start();
    rec.recording = true;
    $('#recBtn').textContent = '停止录音';
    $('#recBtn').classList.add('running');
    $('#recHint').textContent = '录音中…';
    // 录音同时自动开始计时,停止录音不影响计时
    if (!timer.running && timer.sec === 0) startTimer();
  } catch (e) {
    $('#recHint').textContent = '麦克风权限被拒绝';
  }
}

// ---------- 字号 ----------
let fs = 18;
function setFs(d){ fs = Math.max(15, Math.min(30, fs+d)); document.documentElement.style.setProperty('--fs', fs+'px'); }

function escapeHtml(s){ return (''+s).replace(/[&<>]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;'}[c])); }

// ---------- 绑定 ----------
$('#refreshBtn').onclick = () => location.reload();
$('#backBtn').onclick = closeReader;
$('#favBtn').onclick = () => { if (curItem){ toggleFav(curItem); updateFavBtn(); } };
$('#zoomIn').onclick = () => setFs(2);
$('#zoomOut').onclick = () => setFs(-2);
$('#pinyinBtn').onclick = () => {
  const on = $('#rBody').classList.toggle('show-pinyin');
  $('#pinyinBtn').classList.toggle('on', on);
};
$('#tStart').onclick = () => { timer.running ? pauseTimer() : startTimer(); };
$('#tDone').onclick = doneTimer;
$('#tReset').onclick = resetTimer;
$('#recBtn').onclick = toggleRec;

let searchTimer = null;
$('#search').oninput = (e) => {
  query = e.target.value;
  clearTimeout(searchTimer);
  searchTimer = setTimeout(render, 200);
};

if ('serviceWorker' in navigator){
  navigator.serviceWorker.register('sw.js').catch(()=>{});
}

init();
