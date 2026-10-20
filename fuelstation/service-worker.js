const CACHE = "fsm-cache-v4";
const SHELL = ["./", "./index.html", "./styles.css", "./manifest.webmanifest",
  "./js/app.js", "./js/store.js", "./js/auth.js", "./js/ui.js", "./js/calc.js", "./js/forms.js", "./js/catalogue.js",
  "./js/views/home.js", "./js/views/daily.js", "./js/views/customers.js", "./js/views/payments.js", "./js/views/setup.js", "./js/views/dashboard.js",
  "./icons/icon-192.png", "./icons/icon-512.png", "./icons/apple-touch-icon.png", "./icons/favicon-32.png"];

self.addEventListener("install", (e) => e.waitUntil(caches.open(CACHE).then((c) => c.addAll(SHELL)).then(() => self.skipWaiting())));
self.addEventListener("activate", (e) => e.waitUntil(
  caches.keys().then((ks) => Promise.all(ks.filter((k) => k !== CACHE).map((k) => caches.delete(k)))).then(() => self.clients.claim())));

// Network first so updates show up immediately; fall back to cache when offline.
self.addEventListener("fetch", (e) => {
  if (e.request.method !== "GET" || new URL(e.request.url).pathname.includes("/api/")) return;
  e.respondWith(fetch(e.request).then((res) => {
    if (res.ok && res.type === "basic") { const copy = res.clone(); caches.open(CACHE).then((c) => c.put(e.request, copy)); }
    return res;
  }).catch(() => caches.match(e.request).then((hit) => hit || caches.match("./index.html"))));
});
