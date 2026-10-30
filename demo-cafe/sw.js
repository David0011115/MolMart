/* MolMart: офлайн-режим. Сначала сеть (чтобы цены были свежими), без сети — сохранённая копия. */
/* Имя кэша берётся из адреса сайта (папка репозитория), поэтому у каждого заказчика оно своё, править sw.js не нужно.
   Чистим только свои старые кэши (по префиксу), чужие сайты на том же домене не трогаем. */
const SCOPE_ID = new URL(self.registration.scope).pathname.replace(/[^a-z0-9]+/gi, "-").replace(/^-|-$/g, "") || "root";
const PREFIX = "qr-" + SCOPE_ID + "-";
const CACHE = PREFIX + "v3";
const LEGACY = ["molmart-v2"];
const CORE = ["./", "index.html", "config.js", "products.js", "prices.csv", "manifest.json", "icon-192.png", "icon-512.png", "fonts/Onest-var.woff2", "fonts/Unbounded-var.woff2"];
self.addEventListener("install", e => { e.waitUntil(caches.open(CACHE).then(c => c.addAll(CORE)).then(() => self.skipWaiting())); });
self.addEventListener("activate", e => { e.waitUntil(caches.keys().then(ks => Promise.all(ks.filter(k => (k.startsWith(PREFIX) && k !== CACHE) || LEGACY.includes(k)).map(k => caches.delete(k)))).then(() => self.clients.claim())); });
self.addEventListener("fetch", e => {
  const url = new URL(e.request.url);
  if (e.request.method !== "GET" || url.origin !== location.origin) return;
  const key = url.pathname.endsWith("prices.csv") ? "prices.csv" : e.request;
  e.respondWith(
    fetch(e.request).then(r => { if (r.ok) { const copy = r.clone(); caches.open(CACHE).then(c => c.put(key, copy)); } return r; })
      .catch(() => caches.match(key, {ignoreSearch: true}).then(r => r || caches.match("index.html")))
  );
});
