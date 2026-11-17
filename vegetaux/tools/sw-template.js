// Herbier Vivant : fonctionnement hors connexion.
// Généré par tools/build.py ; la version change à chaque mise à jour des données.
const VERSION = "herbier-__VERSION__";
const SHELL = ["./", "index.html", "manifest.webmanifest", "icon-192.png", "icon-512.png", "apple-touch-icon.png"];
const IMAGES = __IMAGES__;

self.addEventListener("install", e => {
  e.waitUntil((async () => {
    const c = await caches.open(VERSION);
    await c.addAll(SHELL);
    self.skipWaiting();
    // Photos mises en cache en arrière-plan, par petits lots, pour l'usage hors connexion
    for (let i = 0; i < IMAGES.length; i += 20) {
      await Promise.all(IMAGES.slice(i, i + 20).map(u => c.match(u).then(hit => hit || c.add(u)).catch(() => {})));
    }
  })());
});

self.addEventListener("activate", e => {
  e.waitUntil((async () => {
    for (const k of await caches.keys()) if (k !== VERSION) await caches.delete(k);
    await self.clients.claim();
  })());
});

self.addEventListener("fetch", e => {
  const req = e.request;
  if (req.method !== "GET") return;
  const url = new URL(req.url);
  const sameOrigin = url.origin === location.origin;
  const fonts = /fonts\.(googleapis|gstatic)\.com$/.test(url.hostname);
  if (!sameOrigin && !fonts) return;
  // Page : réseau d'abord (pour recevoir les mises à jour), cache si hors connexion
  if (req.mode === "navigate") {
    e.respondWith(fetch(req).then(r => { caches.open(VERSION).then(c => c.put("index.html", r.clone())); return r; })
      .catch(() => caches.match("index.html")));
    return;
  }
  // Photos, icônes, polices : cache d'abord
  e.respondWith(caches.match(req).then(hit => hit || fetch(req).then(r => {
    if (r.ok || r.type === "opaque") { const copy = r.clone(); caches.open(VERSION).then(c => c.put(req, copy)); }
    return r;
  })));
});
