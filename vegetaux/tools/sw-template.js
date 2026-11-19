// Herbier Vivant : fonctionnement hors connexion.
// Généré par tools/build.py ; la version change à chaque mise à jour.
// L'application est gardée dès l'installation ; chaque photo est gardée dès qu'elle a été vue une fois
// (plus de 2000 photos : tout télécharger d'un coup serait trop lourd pour un téléphone).
const VERSION = "herbier-__VERSION__";
const PHOTOS = "herbier-photos-v1";
const SHELL = ["./", "index.html", "manifest.webmanifest", "icon-192.png", "icon-512.png", "apple-touch-icon.png"];
const KNOWN = new Set(__IMAGES__);

self.addEventListener("install", e => {
  e.waitUntil(caches.open(VERSION).then(c => c.addAll(SHELL)).then(() => self.skipWaiting()));
});

self.addEventListener("activate", e => {
  e.waitUntil((async () => {
    for (const k of await caches.keys()) if (k !== VERSION && k !== PHOTOS) await caches.delete(k);
    // Supprime les photos qui ne font plus partie de l'application
    const pc = await caches.open(PHOTOS);
    for (const req of await pc.keys()) {
      const path = new URL(req.url).pathname.split("/").slice(-3).join("/");
      if (!KNOWN.has(path)) await pc.delete(req);
    }
    await self.clients.claim();
  })());
});

self.addEventListener("message", e => {
  // Téléchargement à la demande (par exemple les photos d'un niveau) pour l'usage hors connexion
  if (e.data && e.data.type === "precache" && Array.isArray(e.data.files)) {
    e.waitUntil(caches.open(PHOTOS).then(async c => {
      for (let i = 0; i < e.data.files.length; i += 12) {
        await Promise.all(e.data.files.slice(i, i + 12).map(u => c.match(u).then(hit => hit || c.add(u)).catch(() => {})));
      }
    }));
  }
});

self.addEventListener("fetch", e => {
  const req = e.request;
  if (req.method !== "GET") return;
  const url = new URL(req.url);
  const sameOrigin = url.origin === location.origin;
  const fonts = /fonts\.(googleapis|gstatic)\.com$/.test(url.hostname);
  if (!sameOrigin && !fonts) return;
  if (req.mode === "navigate") {
    e.respondWith(fetch(req).then(r => { const copy = r.clone(); caches.open(VERSION).then(c => c.put("index.html", copy)); return r; })
      .catch(() => caches.match("index.html")));
    return;
  }
  const bucket = url.pathname.includes("/photos/") ? PHOTOS : VERSION;
  e.respondWith(caches.match(req).then(hit => hit || fetch(req).then(r => {
    if (r.ok || r.type === "opaque") { const copy = r.clone(); caches.open(bucket).then(c => c.put(req, copy)); }
    return r;
  })));
});
