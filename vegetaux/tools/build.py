"""Assemble l'application : injecte le catalogue et les crédits photo dans template.html.

Produit index.html (page autonome, installable sur téléphone) et sw.js (hors connexion).
Usage : python3 tools/build.py
"""
import json, os, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FIELDS = ("id", "lat", "fr", "fam", "type", "orig", "lvl", "tip", "diff", "conf")
catalog = json.load(open(os.path.join(ROOT, "data/catalog.json")))
credits = json.load(open(os.path.join(ROOT, "data/photo_credits.json")))

img = {}
for pid, slots in credits.items():
    ok = {k: m for k, m in slots.items() if os.path.exists(os.path.join(ROOT, m["file"]))}
    if ok:
        img[pid] = ok
# On garde les plantes qui ont leurs 4 photos (au moins 3 pour celles choisies à la main)
plants = [{k: p[k] for k in FIELDS} for p in catalog if len(img.get(p["id"], {})) >= (3 if p.get("curated") else 4)]
keep = {p["id"] for p in plants}
for p in plants:
    p["conf"] = [c for c in p["conf"] if c in keep]
img = {k: v for k, v in img.items() if k in keep}

tpl = open(os.path.join(ROOT, "template.html")).read()
dump = lambda o: json.dumps(o, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
page = (tpl.replace("/*PLANTS*/[]", dump(plants))
           .replace("/*IMAGES*/{}", dump(img))
           )
page = page.replace('/*SHARE_URL*/""', '""')  # le lien de partage est l'adresse réelle de la page
# Version installable (PWA) : manifeste, icônes, fonctionnement hors connexion
import hashlib
files = sorted(m["file"] for slots in img.values() for m in slots.values())
version = hashlib.sha1((page + "".join(files)).encode()).hexdigest()[:10]
open(os.path.join(ROOT, "sw.js"), "w").write(
    open(os.path.join(ROOT, "tools/sw-template.js")).read()
    .replace("__VERSION__", version)
    .replace("__IMAGES__", json.dumps(files)))
pwa_head = (
    '<link rel="manifest" href="manifest.webmanifest">\n'
    '<meta name="theme-color" content="#2c5a3a">\n'
    '<link rel="icon" href="icon-192.png">\n'
    '<link rel="apple-touch-icon" href="apple-touch-icon.png">\n'
    '<meta name="apple-mobile-web-app-capable" content="yes">\n'
    '<meta name="mobile-web-app-capable" content="yes">\n'
    '<meta name="apple-mobile-web-app-title" content="Herbier">\n'
    '<meta name="apple-mobile-web-app-status-bar-style" content="default">\n')
pwa_script = ('<script>if("serviceWorker" in navigator && (location.protocol==="https:"||location.hostname==="localhost"))'
              '{addEventListener("load",()=>navigator.serviceWorker.register("sw.js").catch(()=>{}))}</script>\n')
open(os.path.join(ROOT, "index.html"), "w").write(
    '<!doctype html>\n<html lang="fr">\n<head>\n<meta charset="utf-8">\n'
    '<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">\n'
    + pwa_head + '</head>\n<body>\n' + page + '\n' + pwa_script + '</body>\n</html>\n')
print(f"{len(plants)} végétaux, {sum(map(len, img.values()))} photos")
