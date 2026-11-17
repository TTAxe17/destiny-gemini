"""Télécharge jusqu'à 3 photos libres par végétal depuis iNaturalist.

Usage : python3 tools/fetch_inat.py
Reprend là où il s'est arrêté (data/photos.json + img/<id>-<n>.jpg).
Cadence : environ 1 requête par seconde, comme le demande iNaturalist.
"""
import json, os, re, time, urllib.parse, urllib.request, urllib.error

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
UA = "PlantQuizBuilder/1.0 (educational, low-volume)"
PER_PLANT = 3
OPEN = {"cc0", "cc-by", "cc-by-sa", "cc-by-nc", "cc-by-nc-sa", "cc-by-nd", "cc-by-nc-nd"}

plants = json.load(open(os.path.join(ROOT, "data/plants.json")))
out_path = os.path.join(ROOT, "data/photos.json")
photos = json.load(open(out_path)) if os.path.exists(out_path) else {}
os.makedirs(os.path.join(ROOT, "img"), exist_ok=True)

# Noms utilisés par iNaturalist quand ils diffèrent de ceux de l'appli
ALIASES = {
    "platanus-hispanica": "Platanus × hispanica",
    "photinia-fraseri": "Photinia × fraseri",
    "forsythia-intermedia": "Forsythia × intermedia",
    "elaeagnus-ebbingei": "Elaeagnus × submacrophylla",
    "abelia-grandiflora": "Abelia × grandiflora",
    "spiraea-vanhouttei": "Spiraea × vanhouttei",
    "mahonia-aquifolium": "Berberis aquifolium",
    "nepeta-faassenii": "Nepeta × faassenii",
    "lavandula-intermedia": "Lavandula × intermedia",
    "cuprocyparis-leylandii": "Cupressus × leylandii",
    "sorbus-aria": "Sorbus aria",
    "pennisetum-alopecuroides": "Cenchrus purpurascens",
    "hosta-sieboldiana": "Hosta sieboldiana",
    "heuchera-micrantha": "Heuchera micrantha",
}


def get(url, binary=False):
    delay = 10
    for attempt in range(8):
        req = urllib.request.Request(url, headers={"User-Agent": UA})
        try:
            with urllib.request.urlopen(req, timeout=40) as r:
                data = r.read()
            time.sleep(1.1)
            return data if binary else json.loads(data)
        except urllib.error.HTTPError as e:
            if e.code in (429, 500, 502, 503):
                wait = int(e.headers.get("Retry-After") or delay)
                print(f"  {e.code}, attente {wait}s", flush=True)
                time.sleep(wait)
                delay = min(delay * 2, 300)
                continue
            print(f"  HTTP {e.code} {url}", flush=True)
            time.sleep(1.1)
            return None
        except Exception as e:
            print(f"  erreur réseau ({e}), nouvelle tentative", flush=True)
            time.sleep(20)
    return None


def norm(s):
    return re.sub(r"\s+", " ", s.replace("×", "x").replace("× ", "x ").lower()).strip()


def find_taxon(name):
    q = urllib.parse.urlencode({"q": name, "per_page": 10, "is_active": "true"})
    d = get("https://api.inaturalist.org/v1/taxa?" + q)
    res = (d or {}).get("results", [])
    want = norm(name).replace("x ", "")
    for t in res:
        if norm(t["name"]).replace("x ", "") == want:
            return t
    # sinon, premier résultat au rang espèce/hybride/genre dont le nom commence pareil
    for t in res:
        if t.get("rank") in ("species", "hybrid", "variety", "genus") and norm(t["name"]).split(" ")[0] == want.split(" ")[0]:
            return t
    return None


def save():
    json.dump(photos, open(out_path, "w"), ensure_ascii=False, indent=1)


for p in plants:
    pid = p["id"]
    have = photos.get(pid)
    if have and all(os.path.exists(os.path.join(ROOT, ph["file"])) for ph in have) and len(have) >= 1:
        continue
    name = ALIASES.get(pid, p["lat"])
    print(pid, "→", name, flush=True)
    t = find_taxon(name)
    if not t:
        print("  taxon introuvable", flush=True)
        continue
    full = get(f"https://api.inaturalist.org/v1/taxa/{t['id']}")
    tp = ((full or {}).get("results") or [{}])[0].get("taxon_photos", [])
    chosen = []
    for item in tp:
        ph = item.get("photo", {})
        if (ph.get("license_code") or "") not in OPEN:
            continue
        url = ph.get("medium_url") or (ph.get("url") or "").replace("square", "medium")
        if not url:
            continue
        chosen.append(ph | {"_url": url})
        if len(chosen) == PER_PLANT:
            break
    entries = []
    for n, ph in enumerate(chosen, 1):
        data = get(ph["_url"], binary=True)
        if not data:
            continue
        f = f"img/{pid}-{n}.jpg"
        open(os.path.join(ROOT, f), "wb").write(data)
        by = re.sub(r"^\(c\)\s*", "", ph.get("attribution", "")).split(",")[0].strip()
        entries.append({"file": f, "by": by, "lic": ph["license_code"].upper().replace("CC-", "CC ").replace("CC0", "CC0"),
                        "url": f"https://www.inaturalist.org/photos/{ph['id']}", "taxon": t["name"]})
    if entries:
        photos[pid] = entries
        save()
    print(f"  {len(entries)} photo(s) ({t['name']})", flush=True)

missing = [p["id"] for p in plants if not photos.get(p["id"])]
print("TERMINÉ. Sans photo :", missing, flush=True)
