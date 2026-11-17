"""Assemble l'application : injecte les données dans template.html.

Produit :
  app.html   -> page publiée en Artifact (sans <!doctype>, ajouté à la publication)
  index.html -> même page autonome, pour GitHub Pages ou un hébergement web classique
Usage : python3 tools/build.py [URL_DE_PARTAGE]
"""
import json, os, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
plants = json.load(open(os.path.join(ROOT, "data/plants.json")))
photos_path = os.path.join(ROOT, "data/photos.json")
photos = json.load(open(photos_path)) if os.path.exists(photos_path) else {}
share = sys.argv[1] if len(sys.argv) > 1 else "https://claude.ai/artifact/VKobStoCcmh9hH27HKrAtF"

img = {}
for pid, lst in photos.items():
    ok = [{k: m[k] for k in ("file", "by", "lic", "url")} for m in lst if os.path.exists(os.path.join(ROOT, m["file"]))]
    if ok:
        img[pid] = ok

tpl = open(os.path.join(ROOT, "template.html")).read()
dump = lambda o: json.dumps(o, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
page = (tpl.replace("/*PLANTS*/[]", dump(plants))
           .replace("/*IMAGES*/{}", dump(img))
           )
# app.html (page claude.ai) : lien de partage fixe ; index.html (hébergement web) : son adresse réelle
open(os.path.join(ROOT, "app.html"), "w").write(page.replace('/*SHARE_URL*/""', dump(share)))
page = page.replace('/*SHARE_URL*/""', '""')
# Version installable (PWA) : manifeste, icônes, fonctionnement hors connexion
import hashlib
files = sorted(m["file"] for lst in img.values() for m in lst)
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
print(f"{len(plants)} végétaux, {len(img)} avec photos, {sum(map(len, img.values()))} photos")
