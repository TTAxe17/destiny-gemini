"""Récupère une photo libre (Wikimedia Commons) pour chaque végétal.

Usage : python3 tools/fetch_images.py
Reprend là où il s'est arrêté (data/images.json + img/*.jpg).
Cadence lente pour respecter les limites de Wikimedia.
"""
import json, os, re, sys, time, urllib.parse, urllib.request, urllib.error

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
UA = "PlantQuizBuilder/1.0 (https://claude.ai/code; educational, low-volume)"
PAUSE = 1.5
WIDTH = 500

plants = json.load(open(os.path.join(ROOT, "data/plants.json")))
meta_path = os.path.join(ROOT, "data/images.json")
meta = json.load(open(meta_path)) if os.path.exists(meta_path) else {}


def get(url, binary=False):
    delay = 15
    neterr = 0
    for attempt in range(200):
        req = urllib.request.Request(url, headers={"User-Agent": UA})
        try:
            with urllib.request.urlopen(req, timeout=40) as r:
                data = r.read()
            time.sleep(PAUSE)
            return data if binary else json.loads(data)
        except urllib.error.HTTPError as e:
            if e.code == 404:
                time.sleep(PAUSE)
                return None
            if e.code in (429, 503, 502):
                wait = int(e.headers.get("Retry-After") or delay)
                print(f"  {e.code}, attente {wait}s", flush=True)
                time.sleep(wait)
                delay = min(delay * 2, 240)
                if attempt > 8:
                    return None
                continue
            print(f"  HTTP {e.code} {url}", flush=True)
            time.sleep(PAUSE)
            return None
        except Exception as e:  # réseau (proxy momentanément fermé) : on patiente
            neterr += 1
            if neterr in (1, 10, 40):
                print(f"  erreur réseau, nouvelle tentative… ({e})", flush=True)
            if neterr > 150:
                return None
            time.sleep(30)
    return None


def save():
    json.dump(meta, open(meta_path, "w"), ensure_ascii=False, indent=1)


PLATE = re.compile(r"k[oö]e?hler|illustration|sturm|thom[eé]|botanical|plate|flora|tafel|drawing|\.svg$|\.png$|\.tif|(?<![a-z])(map|range)(?![a-z])|distribution|herbarium", re.I)


def pick_from_media(lang, t):
    d = get(f"https://{lang}.wikipedia.org/api/rest_v1/page/media-list/{t}")
    for it in (d or {}).get("items", []):
        if it.get("type") != "image":
            continue
        name = it.get("title", "").replace("File:", "").replace("Fichier:", "")
        if not re.search(r"\.jpe?g$", name, re.I) or PLATE.search(name):
            continue
        srcset = it.get("srcset") or []
        if not srcset:
            continue
        src = srcset[0]["src"].split("?")[0]
        src = ("https:" + src) if src.startswith("//") else src
        src = re.sub(r"/\d+px-", f"/{WIDTH}px-", src)
        return {"src": src, "commons": name}
    return None


def summary(title):
    t = urllib.parse.quote(title.replace(" ", "_"), safe="")
    found = []
    for lang in ("fr", "en"):
        d = get(f"https://{lang}.wikipedia.org/api/rest_v1/page/summary/{t}")
        if d and d.get("thumbnail") and d.get("originalimage"):
            fname = urllib.parse.unquote(d["originalimage"]["source"].split("?")[0].split("/")[-1])
            if not PLATE.search(fname):
                return lang, d, None
            found.append((lang, d))
        elif d:
            found.append((lang, d))
    # Image principale = planche dessinée : chercher une vraie photo dans l'article
    for lang, d in found:
        alt = pick_from_media(lang, t)
        if alt:
            return lang, d, alt
    for lang, d in found:
        if d.get("thumbnail") and d.get("originalimage"):
            return lang, d, None
    return None, None, None


for p in plants:
    pid = p["id"]
    m = meta.get(pid)
    img_file = os.path.join(ROOT, "img", pid + ".jpg")
    if m and m.get("file") and os.path.exists(img_file):
        continue
    title = p.get("wiki") or p["lat"]
    print(pid, "…", flush=True)
    if not m or not m.get("src"):
        lang, d, alt = summary(title)
        if not d:
            print("  pas d'image", flush=True)
            meta[pid] = {"missing": True}
            save()
            continue
        if alt:
            m = {"src": alt["src"], "commons": alt["commons"], "lang": lang}
            meta[pid] = m
            save()
        orig = d.get("originalimage") or {}
    if not m or not m.get("src"):
        orig = d["originalimage"]
        thumb = d["thumbnail"]["source"].split("?")[0]
        fname = urllib.parse.unquote(orig["source"].split("?")[0].split("/")[-1])
        if orig.get("width", 0) > WIDTH and "/thumb/" in thumb:
            src = re.sub(r"/\d+px-", f"/{WIDTH}px-", thumb)
        else:
            src = orig["source"].split("?")[0]
        m = {"src": src, "commons": fname, "page": d.get("content_urls", {}).get("desktop", {}).get("page"), "lang": lang}
        meta[pid] = m
        save()
    data = get(m["src"], binary=True)
    if not data:
        print("  téléchargement impossible", flush=True)
        continue
    # Les vignettes PNG/SVG sont rendues en PNG : on garde l'extension .jpg pour simplifier,
    # le navigateur lit le type réel.
    open(img_file, "wb").write(data)
    m["file"] = f"img/{pid}.jpg"
    m["bytes"] = len(data)
    save()
    print("  ok", len(data), flush=True)

# Crédits (auteur + licence) en lots de 40 fichiers
need = [k for k, v in meta.items() if v.get("commons") and "artist" not in v]
for i in range(0, len(need), 40):
    batch = need[i:i + 40]
    titles = "|".join("File:" + meta[k]["commons"] for k in batch)
    q = urllib.parse.urlencode({"action": "query", "titles": titles, "prop": "imageinfo",
                                "iiprop": "extmetadata", "iiextmetadatafilter": "Artist|LicenseShortName",
                                "format": "json", "formatversion": "2"})
    d = get("https://commons.wikimedia.org/w/api.php?" + q)
    if not d:
        continue
    norm = {n["from"]: n["to"] for n in d.get("query", {}).get("normalized", [])}
    by_title = {pg["title"]: pg for pg in d.get("query", {}).get("pages", [])}
    for k in batch:
        t = "File:" + meta[k]["commons"]
        pg = by_title.get(norm.get(t, t)) or by_title.get(t.replace("_", " "))
        if not pg or "imageinfo" not in pg:
            continue
        em = pg["imageinfo"][0].get("extmetadata", {})
        artist = re.sub(r"<[^>]+>", "", em.get("Artist", {}).get("value", "")).strip()
        meta[k]["artist"] = re.sub(r"\s+", " ", artist)[:80] or "Auteur inconnu"
        meta[k]["license"] = em.get("LicenseShortName", {}).get("value", "")
    save()

missing = [p["id"] for p in plants if not meta.get(p["id"], {}).get("file")]
print("TERMINÉ. Sans image :", missing)
