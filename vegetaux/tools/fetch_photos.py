"""Télécharge, pour chaque plante du catalogue, la meilleure photo de chaque organe
(feuille, fruit, écorce, port) parmi les photos Pl@ntNet disponibles.

Choix de la meilleure photo : on télécharge une version moyenne de plusieurs candidates,
on note leur netteté (variance du laplacien), leur contraste et leur exposition,
puis on télécharge l'original de la mieux notée.

Usage : python3 tools/fetch_photos.py
Sortie : photos/<id>/<organe>.jpg + data/photo_credits.json (reprend là où il s'est arrêté)
"""
import io, json, math, os, threading, time, urllib.request, urllib.error
from concurrent.futures import ThreadPoolExecutor
from PIL import Image, ImageFilter, ImageStat, ImageOps

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
UA = "PlantQuizBuilder/1.0 (educational, low-volume)"
TRY = 14           # candidates examinées par organe (vignettes)
TOP = 3            # meilleures candidates téléchargées en taille moyenne pour juger la netteté
MAX_SIDE = 1000    # taille finale (bonne qualité sur téléphone, poids raisonnable)
QUALITY = 80
OPEN_LIC = ("cc-by", "cc-by-sa", "cc0", "public")

catalog = json.load(open(os.path.join(ROOT, "data/catalog.json")))
index = json.load(open(os.path.join(ROOT, "data/media_index.json")))
cred_path = os.path.join(ROOT, "data/photo_credits.json")
credits = json.load(open(cred_path)) if os.path.exists(cred_path) else {}
lock = threading.Lock()


def get(url):
    for attempt in range(5):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=60) as r:
                return r.read()
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return None
            time.sleep(5 * (attempt + 1))
        except Exception:
            time.sleep(5 * (attempt + 1))
    return None


def score(data):
    try:
        im = ImageOps.exif_transpose(Image.open(io.BytesIO(data))).convert("L")
    except Exception:
        return -1e9
    im.thumbnail((400, 400))
    lap = im.filter(ImageFilter.Kernel((3, 3), [0, 1, 0, 1, -4, 1, 0, 1, 0], 1, 128))
    sharp = ImageStat.Stat(lap).var[0]
    st = ImageStat.Stat(im)
    mean, std = st.mean[0], st.stddev[0]
    s = math.log(sharp + 1) * 2 + math.log(std + 1)
    if mean < 55 or mean > 205:
        s -= 2.5          # photo trop sombre ou surexposée
    return s


def medium(url):
    return url.replace("/image/o/", "/image/m/")


def small(url):
    return url.replace("/image/o/", "/image/s/")


def colors(data):
    """Parts de vert, de blanc (fleurs), de brun/gris, de ciel (tiers haut) et de couleurs de fruits."""
    try:
        im = Image.open(io.BytesIO(data)).convert("HSV").resize((60, 60))
    except Exception:
        return None
    px = list(im.get_flattened_data() if hasattr(im, "get_flattened_data") else im.getdata())
    n = len(px)
    top = px[: n // 3]
    green = sum(1 for h, s, v in px if 45 <= h <= 125 and s > 60 and v > 40) / n
    white = sum(1 for h, s, v in px if s < 35 and v > 215) / n
    brown = sum(1 for h, s, v in px if (s < 70 and 40 < v < 200) or (5 <= h <= 35 and s > 50 and v < 170)) / n
    sky = sum(1 for h, s, v in top if (130 <= h <= 180 and s > 35 and v > 120) or (s < 25 and v > 190)) / len(top)
    fruit = sum(1 for h, s, v in px if ((h < 22 or h > 200) and s > 90 and v > 60) or (v < 45)) / n
    return green, white, brown, sky, fruit


def fit(organ, c):
    """Note de cohérence entre l'organe demandé et les couleurs de la photo."""
    if not c:
        return -9
    green, white, brown, sky, fruit = c
    if organ == "leaf":
        return 2.5 * green - 2.5 * white
    if organ == "bark":
        return 3.0 * brown - 2.5 * green - 2.0 * white - 1.5 * sky
    if organ == "habit":
        return 2.5 * sky + 0.5 * green - 1.0 * white - 4.0 * max(0.0, green - 0.7)
    if organ == "fruit":
        return 2.0 * fruit - 1.0 * white
    return -1.0 * white   # fleur


def best_photo(cands, organ):
    cands = [c for c in cands if any(c["lic"].lower().startswith(l) for l in OPEN_LIC)] or cands
    pre = []
    for c in cands[:TRY]:
        d = get(small(c["url"]))
        if d:
            pre.append((fit(organ, colors(d)), c))
    pre.sort(key=lambda x: -x[0])
    scored = []
    for f, c in pre[:TOP]:
        d = get(medium(c["url"]))
        if d:
            scored.append((score(d) + 3 * f, c))
    scored.sort(key=lambda x: -x[0])
    for s, c in scored:
        data = get(c["url"])
        if not data:
            continue
        try:
            im = ImageOps.exif_transpose(Image.open(io.BytesIO(data))).convert("RGB")
        except Exception:
            continue
        if min(im.size) < 500:
            continue
        im.thumbnail((MAX_SIDE, MAX_SIDE), Image.LANCZOS)
        return im, c, s
    return None, None, None


def work(p):
    pid = p["id"]
    org = index[p["lat"]]["organs"]
    os.makedirs(os.path.join(ROOT, "photos", pid), exist_ok=True)
    out = credits.get(pid, {})
    for slot, organ in p["slots"].items():
        f = f"photos/{pid}/{slot}.jpg"
        if slot in out and os.path.exists(os.path.join(ROOT, f)):
            continue
        im, c, s = best_photo(org.get(organ, []), organ)
        if not im:
            continue
        im.save(os.path.join(ROOT, f), "JPEG", quality=QUALITY, optimize=True, progressive=True)
        out[slot] = {"file": f, "organ": organ, "by": c["by"], "lic": c["lic"].upper(), "src": c["src"]}
    with lock:
        credits[pid] = out
        json.dump(credits, open(cred_path, "w"), ensure_ascii=False)
        print(len(credits), pid, "→", ", ".join(sorted(out)), flush=True)


todo = [p for p in catalog if not p.get("curated") and len(credits.get(p["id"], {})) < 4]
print(len(catalog), "plantes,", len(todo), "à traiter", flush=True)
with ThreadPoolExecutor(6) as ex:
    list(ex.map(work, todo))
incomplete = [p["id"] for p in catalog if not p.get("curated") and len(credits.get(p["id"], {})) < 4]
print("TERMINÉ. Incomplètes :", incomplete, flush=True)
