// 简单离线缓存:应用外壳走「缓存优先」,新闻数据走「网络优先」(拿最新,断网回退缓存)
const SHELL = 'broadcast-shell-v2';
const SHELL_FILES = [
  './', './index.html', './style.css', './app.js',
  './manifest.webmanifest', './icon.svg'
];

self.addEventListener('install', (e) => {
  e.waitUntil(caches.open(SHELL).then(c => c.addAll(SHELL_FILES)).then(() => self.skipWaiting()));
});

self.addEventListener('activate', (e) => {
  e.waitUntil(
    caches.keys().then(keys =>
      Promise.all(keys.filter(k => k !== SHELL).map(k => caches.delete(k)))
    ).then(() => self.clients.claim())
  );
});

self.addEventListener('fetch', (e) => {
  const url = new URL(e.request.url);
  // 新闻数据:网络优先,失败回退缓存
  if (url.pathname.includes('/data/')) {
    e.respondWith(
      fetch(e.request).then(res => {
        const copy = res.clone();
        caches.open(SHELL).then(c => c.put(e.request, copy));
        return res;
      }).catch(() => caches.match(e.request))
    );
    return;
  }
  // 其余:缓存优先
  e.respondWith(caches.match(e.request).then(r => r || fetch(e.request)));
});
