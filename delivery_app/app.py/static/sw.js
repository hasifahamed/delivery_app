const CACHE = "noe-v1"; // change to v2, v3... after you update images or icons
const ASSETS = ["/static/logo.svg", "/static/hero.jpg", "/static/icon-192.png", "/static/icon-512.png"];

self.addEventListener("install", e => {
  e.waitUntil(caches.open(CACHE).then(c => c.addAll(ASSETS)));
  self.skipWaiting();
});

self.addEventListener("activate", e => {
  e.waitUntil(caches.keys().then(keys =>
    Promise.all(keys.filter(k => k !== CACHE).map(k => caches.delete(k)))));
  self.clients.claim();
});

self.addEventListener("fetch", e => {
  const u = new URL(e.request.url);
  if (e.request.method !== "GET" || u.origin !== location.origin) return;
  if (u.pathname.startsWith("/static/")) {
    e.respondWith(caches.match(e.request).then(r => r || fetch(e.request)));
    return;
  }
  if (e.request.mode === "navigate") {
    e.respondWith(fetch(e.request).catch(() => new Response(
      "<meta name=viewport content='width=device-width,initial-scale=1'><body style='font-family:sans-serif;padding:32px;text-align:center'><h1>No internet</h1><p>Please connect and try again, or call +91 95667 00534.</p></body>",
      {headers: {"Content-Type": "text/html"}})));
  }
});