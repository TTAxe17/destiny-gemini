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
share = sys.argv[1] if len(sys.argv) > 1 else ""

img = {}
for pid, lst in photos.items():
    ok = [{k: m[k] for k in ("file", "by", "lic", "url")} for m in lst if os.path.exists(os.path.join(ROOT, m["file"]))]
    if ok:
        img[pid] = ok

tpl = open(os.path.join(ROOT, "template.html")).read()
dump = lambda o: json.dumps(o, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
page = (tpl.replace("/*PLANTS*/[]", dump(plants))
           .replace("/*IMAGES*/{}", dump(img))
           .replace('/*SHARE_URL*/""', dump(share)))
open(os.path.join(ROOT, "app.html"), "w").write(page)
open(os.path.join(ROOT, "index.html"), "w").write(
    '<!doctype html>\n<html lang="fr">\n<head>\n<meta charset="utf-8">\n'
    '<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">\n'
    '</head>\n<body>\n' + page + '\n</body>\n</html>\n')
print(f"{len(plants)} végétaux, {len(img)} avec photos, {sum(map(len, img.values()))} photos")
