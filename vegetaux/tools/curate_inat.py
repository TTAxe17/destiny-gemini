"""Plantes de pépinière absentes des données Pl@ntNet : photos choisies à la main sur iNaturalist.

Étape 1 : python3 tools/curate_inat.py sheets  -> planches numérotées de 16 photos par plante
Étape 2 : on note les meilleurs numéros dans data/curated_picks.json, par exemple
          {"Photinia × fraseri": {"leaf": 3, "fruit": [7, "flower"], "bark": 12, "habit": 1}}
Étape 3 : python3 tools/curate_inat.py fetch   -> photos/<id>/<case>.jpg + crédits
"""
import io, json, os, sys, time, urllib.parse, urllib.request
from PIL import Image, ImageDraw, ImageFont, ImageOps

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
UA = "PlantQuizBuilder/1.0 (educational, low-volume)"
LIC = "cc-by,cc-by-sa,cc-by-nc,cc-by-nc-sa,cc0"
CAND = os.path.join(ROOT, "data/inat_candidates.json")
PICKS = os.path.join(ROOT, "data/curated_picks.json")
SHEETS = sys.argv[2] if len(sys.argv) > 2 else os.path.join(ROOT, "..", "sheets")

# nom de l'appli -> nom utilisé par iNaturalist
NAMES = {
    "× Cuprocyparis leylandii": "Hesperotropsis leylandii",
    "Mahonia × media": "Berberis × media",
    "Elaeagnus × ebbingei": "Elaeagnus × submacrophylla",
}
CURATE = [
    "Photinia × fraseri", "Forsythia × intermedia", "Lagerstroemia indica", "Choisya ternata",
    "Abelia × grandiflora", "Spiraea × vanhouttei", "Deutzia scabra", "Acer palmatum", "Prunus serrulata",
    "Phyllostachys aurea", "Agapanthus africanus", "Nassella tenuissima", "Oenothera lindheimeri",
    "Nepeta × faassenii", "Salvia yangii", "Hosta sieboldiana", "Heuchera micrantha", "Phormium tenax",
    "Kniphofia uvaria", "Lonicera nitida", "Ilex crenata", "Osmanthus heterophyllus", "Pieris japonica",
    "Hydrangea paniculata", "Lavandula × intermedia", "Cedrus libani", "× Cuprocyparis leylandii",
    "Phoenix canariensis", "Camellia japonica", "Fatsia japonica", "Skimmia japonica", "Ophiopogon japonicus",
    "Metasequoia glyptostroboides", "Araucaria araucana", "Eucalyptus gunnii", "Grevillea rosmarinifolia",
    "Dicksonia antarctica", "Bougainvillea spectabilis", "Washingtonia filifera", "Magnolia × soulangeana",
    "Chaenomeles speciosa", "Weigela florida", "Viburnum plicatum", "Hamamelis × intermedia",
    "Trachelospermum jasminoides", "Clematis montana", "Wisteria floribunda", "Mahonia × media",
    "Koelreuteria paniculata", "Ceanothus thyrsiflorus", "Magnolia stellata", "Viburnum × bodnantense",
]


def get(url, binary=False):
    for attempt in range(6):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=60) as r:
                d = r.read()
            time.sleep(1.0)
            return d if binary else json.loads(d)
        except Exception:
            time.sleep(10 * (attempt + 1))
    return None


def candidates(name):
    """16 photos variées : observations bien notées, observations en fruits, et photos de détail
    (les dernières photos d'une observation montrent souvent le tronc, les rameaux ou le port)."""
    def obs(extra):
        q = urllib.parse.urlencode(dict({"taxon_name": NAMES.get(name, name), "quality_grade": "research", "photos": "true",
                                         "photo_license": LIC, "order_by": "votes", "per_page": 30}, **extra))
        return (get("https://api.inaturalist.org/v1/observations?" + q) or {}).get("results", [])

    def item(ph):
        url = ph.get("url", "")
        return {"id": ph["id"], "small": url.replace("square", "small"), "large": url.replace("square", "large"),
                "by": (ph.get("attribution") or "").replace("(c) ", "").split(",")[0],
                "lic": ph["license_code"].upper(), "src": f"https://www.inaturalist.org/photos/{ph['id']}"}

    ok = lambda ph: (ph.get("license_code") or "") in LIC.split(",")
    out, seen = [], set()

    def add(ph, cap):
        if ok(ph) and ph["id"] not in seen and len(out) < cap:
            seen.add(ph["id"]); out.append(item(ph))

    general = obs({})
    for o in general:                       # 1re photo des observations les mieux notées
        if o.get("photos"): add(o["photos"][0], 6)
    for o in obs({"term_id": 12, "term_value_id": 14}):   # plantes en fruits
        if o.get("photos"): add(o["photos"][0], 11)
    for o in general:                       # photos de détail (2e, 3e… de chaque observation)
        for ph in o.get("photos", [])[1:]:
            add(ph, 16)
    return out[:16]


def sheets():
    os.makedirs(SHEETS, exist_ok=True)
    cand = json.load(open(CAND)) if os.path.exists(CAND) else {}
    for n in CURATE:
        if n not in cand:
            cand[n] = candidates(n)
            json.dump(cand, open(CAND, "w"), ensure_ascii=False)
            print(n, len(cand[n]), flush=True)
    font = ImageFont.load_default(size=26) if hasattr(ImageFont, "load_default") else None
    T = 200
    for k in range(0, len(CURATE), 2):
        pair = CURATE[k:k + 2]
        sheet = Image.new("RGB", (len(pair) * 4 * T + 20, 4 * T + 40), "white")
        d = ImageDraw.Draw(sheet)
        for pi, n in enumerate(pair):
            ox = pi * (4 * T + 20)
            d.text((ox + 4, 4), n, fill="black", font=font)
            for i, c in enumerate(cand[n]):
                data = get(c["small"], binary=True)
                if not data:
                    continue
                im = ImageOps.fit(Image.open(io.BytesIO(data)).convert("RGB"), (T - 4, T - 4))
                x, y = ox + (i % 4) * T, 40 + (i // 4) * T
                sheet.paste(im, (x, y))
                d.rectangle([x, y, x + 34, y + 30], fill="black")
                d.text((x + 4, y + 1), str(i), fill="yellow", font=font)
        sheet.save(os.path.join(SHEETS, f"sheet{k // 2:02d}.jpg"), quality=80)
        print("planche", k // 2, pair, flush=True)


def fetch():
    import re, unicodedata
    cand = json.load(open(CAND))
    picks = json.load(open(PICKS))
    cat = {p["lat"]: p for p in json.load(open(os.path.join(ROOT, "data/catalog.json")))}
    old = {p["lat"]: p for p in json.load(open(os.path.join(ROOT, "data/plants.json")))}
    cred_path = os.path.join(ROOT, "data/photo_credits.json")
    credits = json.load(open(cred_path)) if os.path.exists(cred_path) else {}
    for n, pk in picks.items():
        pid = (cat.get(n) or old.get(n) or {}).get("id") or re.sub(r"[^a-z0-9]+", "-", unicodedata.normalize("NFD", n).encode("ascii", "ignore").decode().lower()).strip("-")
        os.makedirs(os.path.join(ROOT, "photos", pid), exist_ok=True)
        out = {}
        for slot, v in pk.items():
            idx, organ = (v if isinstance(v, list) else [v, slot])
            c = cand[n][idx]
            data = get(c["large"], binary=True)
            if not data:
                continue
            im = ImageOps.exif_transpose(Image.open(io.BytesIO(data))).convert("RGB")
            im.thumbnail((1000, 1000), Image.LANCZOS)
            f = f"photos/{pid}/{slot}.jpg"
            im.save(os.path.join(ROOT, f), "JPEG", quality=80, optimize=True, progressive=True)
            out[slot] = {"file": f, "organ": organ, "by": c["by"], "lic": c["lic"], "src": c["src"]}
        credits[pid] = out
        json.dump(credits, open(cred_path, "w"), ensure_ascii=False)
        print(pid, sorted(out), flush=True)


if __name__ == "__main__":
    {"sheets": sheets, "fetch": fetch}[sys.argv[1]]()
