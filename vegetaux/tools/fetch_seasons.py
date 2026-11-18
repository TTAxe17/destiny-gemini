"""Photos du mode Saisons : fleur de printemps, feuillage d'automne, silhouette d'hiver.

Sources :
- Pl@ntNet (data/season_index.json, photos datées, hémisphère Nord) ;
- pour les plantes de pépinière absentes de Pl@ntNet : iNaturalist, avec ses annotations
  « en fleur » (printemps), « feuilles colorées » (automne) et « sans feuilles » (hiver).
Pour chaque saison, les candidates sont notées sur leurs couleurs (couleurs chaudes en automne,
peu de vert et du ciel en hiver, fleur colorée au printemps) puis sur leur netteté.
Sortie : photos/<id>/{spring,autumn,winter}.jpg + crédits dans data/photo_credits.json
"""
import io, json, math, os, threading, time, urllib.parse, urllib.request, urllib.error
from concurrent.futures import ThreadPoolExecutor
from PIL import Image, ImageFilter, ImageStat, ImageOps

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
UA = "PlantQuizBuilder/1.0 (educational, low-volume)"
MAX_SIDE, QUALITY, TRY, TOP = 900, 78, 14, 3
SLOTS = {"spring": "spring_flower", "autumn": "autumn_leaf", "winter": "winter_habit"}
INAT = {  # annotation iNaturalist et mois, pour les plantes sans données Pl@ntNet
    "spring": {"term_id": 12, "term_value_id": 13, "month": "3,4,5"},
    "autumn": {"term_id": 36, "term_value_id": 39, "month": "9,10,11"},
    "winter": {"term_id": 36, "term_value_id": 40, "month": "12,1,2"},
}
EVERGREEN = ("persistant", "Palmier", "Conifère persistant", "Succulente")

catalog = json.load(open(os.path.join(ROOT, "data/catalog.json")))
seasons = json.load(open(os.path.join(ROOT, "data/season_index.json")))
cred_path = os.path.join(ROOT, "data/photo_credits.json")
credits = json.load(open(cred_path))
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


def colors(data):
    try:
        im = Image.open(io.BytesIO(data)).convert("HSV").resize((60, 60))
    except Exception:
        return None
    px = list(im.get_flattened_data() if hasattr(im, "get_flattened_data") else im.getdata())
    n, top = len(px), px[: len(px) // 3]
    green = sum(1 for h, s, v in px if 45 <= h <= 125 and s > 60 and v > 40) / n
    warm = sum(1 for h, s, v in px if (h < 40 or h > 235) and s > 90 and v > 70) / n
    vivid = sum(1 for h, s, v in px if not (45 <= h <= 125) and s > 90 and v > 90) / n
    white = sum(1 for h, s, v in px if s < 35 and v > 215) / n
    sky = sum(1 for h, s, v in top if (130 <= h <= 180 and s > 35 and v > 120) or (s < 25 and v > 190)) / len(top)
    return green, warm, vivid, white, sky


def fit(slot, c, evergreen):
    if not c:
        return -9
    green, warm, vivid, white, sky = c
    if slot == "autumn":
        return 3.0 * warm - 1.0 * white + (0 if evergreen else -1.0 * max(0.0, green - 0.4))
    if slot == "winter":
        return 2.5 * sky + (0.3 * green if evergreen else -2.0 * green) - 0.5 * max(0.0, white - 0.5)
    return 1.5 * (vivid + white * 0.8) - 0.8 * max(0.0, green - 0.5)   # fleur de printemps


def sharp(data):
    try:
        im = ImageOps.exif_transpose(Image.open(io.BytesIO(data))).convert("L")
    except Exception:
        return -1e9
    im.thumbnail((400, 400))
    lap = im.filter(ImageFilter.Kernel((3, 3), [0, 1, 0, 1, -4, 1, 0, 1, 0], 1, 128))
    st = ImageStat.Stat(im)
    s = math.log(ImageStat.Stat(lap).var[0] + 1) * 2 + math.log(st.stddev[0] + 1)
    return s - (2.5 if st.mean[0] < 55 or st.mean[0] > 205 else 0)


def pick(cands, slot, evergreen, small, medium, large):
    pre = []
    for c in cands[:TRY]:
        d = get(small(c))
        if d:
            pre.append((fit(slot, colors(d), evergreen), c))
    pre.sort(key=lambda x: -x[0])
    if not pre or pre[0][0] < (0.15 if slot == "autumn" else 0.05 if slot == "winter" else 0.1):
        return None, None            # aucune photo assez caractéristique de la saison
    best = []
    for f, c in pre[:TOP]:
        d = get(medium(c))
        if d:
            best.append((sharp(d) + 3 * f, c))
    best.sort(key=lambda x: -x[0])
    for _, c in best:
        data = get(large(c), binary=True)
        if not data:
            continue
        try:
            im = ImageOps.exif_transpose(Image.open(io.BytesIO(data))).convert("RGB")
        except Exception:
            continue
        if min(im.size) < 450:
            continue
        im.thumbnail((MAX_SIDE, MAX_SIDE), Image.LANCZOS)
        return im, c
    return None, None


def inat_cands(name, slot):
    q = dict(INAT[slot], taxon_name=name, quality_grade="research", photos="true",
             photo_license="cc-by,cc-by-sa,cc-by-nc,cc-by-nc-sa,cc0", order_by="votes", per_page=20)
    d = get("https://api.inaturalist.org/v1/observations?" + urllib.parse.urlencode(q)) or {}
    out = []
    for o in d.get("results", []):
        ph = (o.get("photos") or [None])[0]
        if ph and ph.get("license_code"):
            u = ph["url"]
            out.append({"small": u.replace("square", "small"), "medium": u.replace("square", "medium"),
                        "large": u.replace("square", "large"), "by": (ph.get("attribution") or "").replace("(c) ", "").split(",")[0],
                        "lic": ph["license_code"].upper(), "src": f"https://www.inaturalist.org/photos/{ph['id']}"})
    time.sleep(1.0)
    return out


INAT_NAMES = {"× Cuprocyparis leylandii": "Hesperotropsis leylandii"}


def work(p):
    pid = p["id"]
    evergreen = any(x in p["type"] for x in EVERGREEN)
    out = credits.get(pid, {})
    os.makedirs(os.path.join(ROOT, "photos", pid), exist_ok=True)
    for slot, key in SLOTS.items():
        if slot in out:
            continue
        if slot == "autumn" and evergreen:
            continue                 # pas de couleurs d'automne pour les persistants
        cands = (seasons.get(p["lat"]) or {}).get(key) or []
        if cands:
            im, c = pick(cands, slot, evergreen, lambda c: c["url"].replace("/image/o/", "/image/s/"),
                         lambda c: c["url"].replace("/image/o/", "/image/m/"), lambda c: c["url"])
        else:
            ic = inat_cands(INAT_NAMES.get(p["lat"], p["lat"]), slot)
            im, c = pick(ic, slot, evergreen, lambda c: c["small"], lambda c: c["medium"], lambda c: c["large"]) if ic else (None, None)
        if im is None:
            continue
        f = f"photos/{pid}/{slot}.jpg"
        im.save(os.path.join(ROOT, f), "JPEG", quality=QUALITY, optimize=True, progressive=True)
        src = "iNaturalist" if "inaturalist" in c.get("src", "") else "Pl@ntNet"
        out[slot] = {"file": f, "organ": {"spring": "flower", "autumn": "leaf", "winter": "habit"}[slot],
                     "by": c.get("by", ""), "lic": c.get("lic", "").upper(), "src": c.get("src", ""), "season": slot}
    with lock:
        credits[pid] = out
        json.dump(credits, open(cred_path, "w"), ensure_ascii=False)
        print(len([1 for v in credits.values() if any(k in v for k in SLOTS)]), pid, "→",
              ", ".join(k for k in SLOTS if k in out), flush=True)


todo = [p for p in catalog if p["id"] in credits and (p["lat"] in seasons or p.get("curated"))
        and not all(k in credits[p["id"]] for k in SLOTS)]
print(len(todo), "plantes", flush=True)
with ThreadPoolExecutor(6) as ex:
    list(ex.map(work, todo))
print("TERMINÉ", {k: sum(1 for v in credits.values() if k in v) for k in SLOTS}, flush=True)
