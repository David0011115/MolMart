/* MolMart: офлайн-режим. Сначала сеть (чтобы цены были свежими), без сети — сохранённая копия. */
const CACHE = "molmart-v1";
const CORE = ["./", "index.html", "prices.csv", "manifest.json", "icon-192.png", "icon-512.png"];
self.addEventListener("install", e => { e.waitUntil(caches.open(CACHE).then(c => c.addAll(CORE)).then(() => self.skipWaiting())); });
self.addEventListener("activate", e => { e.waitUntil(caches.keys().then(ks => Promise.all(ks.filter(k => k !== CACHE).map(k => caches.delete(k)))).then(() => self.clients.claim())); });
self.addEventListener("fetch", e => {
  const url = new URL(e.request.url);
  if (e.request.method !== "GET" || url.origin !== location.origin) return;
  const key = url.pathname.endsWith("prices.csv") ? "prices.csv" : e.request;
  e.respondWith(
    fetch(e.request).then(r => { if (r.ok) { const copy = r.clone(); caches.open(CACHE).then(c => c.put(key, copy)); } return r; })
      .catch(() => caches.match(key, {ignoreSearch: true}).then(r => r || caches.match("index.html")))
  );
});
