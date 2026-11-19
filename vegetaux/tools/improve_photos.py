"""Repère les photos les plus faibles (feuille, fruit, écorce, port) et cherche mieux.

1. Note chaque photo actuelle : cohérence des couleurs avec l'organe + netteté.
2. Pour le cinquième le plus faible de chaque organe, va chercher 20 à 30 nouvelles candidates
   Pl@ntNet (autres pages, mois adaptés : feuille en pleine saison, fruit de juillet à novembre…).
3. Remplace la photo seulement si la meilleure candidate est nettement meilleure.
Usage : python3 tools/improve_photos.py   (journal des remplacements : data/improved.json)
"""
import io, json, math, os, threading, time, urllib.parse, urllib.request, urllib.error
from concurrent.futures import ThreadPoolExecutor
from PIL import Image, ImageFilter, ImageStat, ImageOps

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
UA = "PlantQuizBuilder/1.0 (educational, low-volume)"
DATASETS = ["7a3679ef-5582-4aaa-81f0-8c2545cafc81", "14d5676a-2c54-4f94-9023-1e8dcd822aa0"]
MONTHS = {"leaf": "5,9", "fruit": "7,11", "bark": None, "habit": None}
SHARE = 0.2      # part des photos les plus faibles réexaminées
MARGIN = 1.0     # gain de note minimal pour remplacer

catalog = json.load(open(os.path.join(ROOT, "data/catalog.json")))
media = json.load(open(os.path.join(ROOT, "data/media_index.json")))
cred_path = os.path.join(ROOT, "data/photo_credits.json")
credits = json.load(open(cred_path))
log_path = os.path.join(ROOT, "data/improved.json")
log = json.load(open(log_path)) if os.path.exists(log_path) else {}
lock = threading.Lock()


def get(url, binary=False):
    for attempt in range(5):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=60) as r:
                d = r.read()
            return d if binary else json.loads(d)
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return None
            time.sleep(5 * (attempt + 1))
        except Exception:
            time.sleep(5 * (attempt + 1))
    return None


def colors(im):
    im = im.convert("HSV").resize((60, 60))
    px = list(im.get_flattened_data() if hasattr(im, "get_flattened_data") else im.getdata())
    n, top = len(px), px[: len(px) // 3]
    green = sum(1 for h, s, v in px if 45 <= h <= 125 and s > 60 and v > 40) / n
    white = sum(1 for h, s, v in px if s < 35 and v > 215) / n
    brown = sum(1 for h, s, v in px if (s < 70 and 40 < v < 200) or (5 <= h <= 35 and s > 50 and v < 170)) / n
    sky = sum(1 for h, s, v in top if (130 <= h <= 180 and s > 35 and v > 120) or (s < 25 and v > 190)) / len(top)
    fruit = sum(1 for h, s, v in px if ((h < 22 or h > 200) and s > 90 and v > 60) or (v < 45)) / n
    return green, white, brown, sky, fruit


def fit(organ, c):
    green, white, brown, sky, fruit = c
    return {"leaf": 2.5 * green - 2.5 * white,
            "bark": 3.0 * brown - 2.5 * green - 2.0 * white - 1.5 * sky,
            "habit": 2.5 * sky + 0.5 * green - 1.0 * white - 4.0 * max(0.0, green - 0.7),
            "fruit": 2.0 * fruit - 1.0 * white}.get(organ, -white)


def score(im, organ):
    g = im.convert("L"); g.thumbnail((400, 400))
    lap = g.filter(ImageFilter.Kernel((3, 3), [0, 1, 0, 1, -4, 1, 0, 1, 0], 1, 128))
    st = ImageStat.Stat(g)
    s = math.log(ImageStat.Stat(lap).var[0] + 1) * 2 + math.log(st.stddev[0] + 1)
    s -= 2.5 if st.mean[0] < 55 or st.mean[0] > 205 else 0
    return s + 3 * fit(organ, colors(im))


def more_candidates(key, organ, skip):
    found, seen = [], set(skip)
    for ds in DATASETS:
        for page in range(3):
            params = {"taxonKey": key, "datasetKey": ds, "mediaType": "StillImage", "limit": 300, "offset": page * 300}
            if MONTHS[organ]:
                params["month"] = MONTHS[organ]
            d = get("https://api.gbif.org/v1/occurrence/search?" + urllib.parse.urlencode(params))
            if not d:
                break
            for r in d.get("results", []):
                for m in r.get("media", []):
                    t = m.get("title") or ""
                    o = t.rsplit(":", 1)[-1].strip().lower() if ":" in t else ""
                    u = m.get("identifier") or ""
                    if o == organ and u and u not in seen:
                        seen.add(u)
                        found.append({"url": u, "by": m.get("creator") or m.get("rightsHolder") or "",
                                      "lic": (m.get("license") or "").split("(")[-1].rstrip(")") or "cc-by-sa",
                                      "src": m.get("source") or ""})
            if len(found) >= 30 or d.get("endOfRecords"):
                break
        if len(found) >= 30:
            break
    return found[:30]


def open_img(data):
    try:
        return ImageOps.exif_transpose(Image.open(io.BytesIO(data))).convert("RGB")
    except Exception:
        return None


# 1. Notes actuelles
plants = [p for p in catalog if not p.get("curated") and p["id"] in credits]
current = []
for p in plants:
    for slot, m in credits[p["id"]].items():
        if slot in ("leaf", "fruit", "bark", "habit") and m.get("organ") == slot and not m.get("improved"):
            im = Image.open(os.path.join(ROOT, m["file"])).convert("RGB")
            current.append((slot, score(im, slot), p))
weak = []
for organ in ("leaf", "fruit", "bark", "habit"):
    lst = sorted([c for c in current if c[0] == organ], key=lambda c: c[1])
    weak += lst[: int(len(lst) * SHARE)]
print(len(current), "photos notées,", len(weak), "à réexaminer", flush=True)


def work(item):
    organ, cur, p = item
    pid = p["id"]
    if f"{pid}/{organ}" in log:
        return
    m = media.get(p["lat"]) or {}
    skip = [c["url"] for c in (m.get("organs") or {}).get(organ, [])]
    cands = more_candidates(m.get("key"), organ, skip) if m.get("key") else []
    pre = []
    for c in cands:
        d = get(c["url"].replace("/image/o/", "/image/s/"), binary=True)
        im = open_img(d) if d else None
        if im:
            pre.append((fit(organ, colors(im)), c))
    pre.sort(key=lambda x: -x[0])
    best = None
    for f, c in pre[:4]:
        d = get(c["url"].replace("/image/o/", "/image/m/"), binary=True)
        im = open_img(d) if d else None
        if im:
            s = score(im, organ)
            if not best or s > best[0]:
                best = (s, c)
    result = "gardée"
    if best and best[0] > cur + MARGIN:
        data = get(best[1]["url"], binary=True)
        im = open_img(data) if data else None
        if im and min(im.size) >= 500:
            im.thumbnail((1000, 1000), Image.LANCZOS)
            f = f"photos/{pid}/{organ}.jpg"
            im.save(os.path.join(ROOT, f), "JPEG", quality=80, optimize=True, progressive=True)
            c = best[1]
            with lock:
                credits[pid][organ] = {"file": f, "organ": organ, "by": c["by"], "lic": c["lic"].upper(),
                                       "src": c["src"], "improved": True}
            result = f"remplacée ({cur:.1f} → {best[0]:.1f})"
    with lock:
        log[f"{pid}/{organ}"] = result
        json.dump(credits, open(cred_path, "w"), ensure_ascii=False)
        json.dump(log, open(log_path, "w"), ensure_ascii=False, indent=0)
        print(len(log), pid, organ, result, flush=True)


with ThreadPoolExecutor(6) as ex:
    list(ex.map(work, weak))
print("TERMINÉ :", sum(1 for v in log.values() if v.startswith("remplacée")), "photos remplacées sur", len(log), flush=True)
