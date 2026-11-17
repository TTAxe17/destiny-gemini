"""Construit le catalogue final (data/catalog.json) à partir de :
- data/plants.json      fiches historiques (conseils déjà écrits)
- data/candidates.tsv   nouveaux candidats (niveau, noms, famille, type, origine)
- data/tips_*.json      conseils des nouveaux candidats
- data/media_index.json photos Pl@ntNet disponibles par organe

Une plante est retenue si Pl@ntNet a au moins une photo de feuille, de fruit (ou fleur à défaut),
d'écorce/tige et de port. Les plantes qui ne poussent pas en France sont exclues.
"""
import glob, json, os, re, unicodedata

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EXCLUDE = {"Protea cynaroides", "Strelitzia reginae", "Rosmarinus officinalis"}  # hors climat français / doublon
OLD_LEVEL = {1: 1, 2: 2, 3: 6, 4: 7, 5: 8, 6: 9}


def slug(s):
    s = unicodedata.normalize("NFD", s).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", s.lower().replace("×", "x")).strip("-")


old = json.load(open(os.path.join(ROOT, "data/plants.json")))
index = json.load(open(os.path.join(ROOT, "data/media_index.json")))
tips = {}
for f in sorted(glob.glob(os.path.join(ROOT, "data/tips_*.json"))):
    tips.update(json.load(open(f)))

entries = {}
for p in old:
    lvl = OLD_LEVEL[p["lvl"]]
    if p["type"].startswith("Conifère"):
        lvl = 5
    entries[p["lat"]] = dict(p, lvl=lvl, conf_lat=[q["lat"] for q in old if q["id"] in p["conf"]])
for line in open(os.path.join(ROOT, "data/candidates.tsv")):
    if not line.strip() or line.startswith("#"):
        continue
    lvl, lat, fr, fam, typ, orig = [x.strip() for x in line.split("|")]
    if lat in entries:  # fiche existante : on garde ses textes, on prend le nouveau niveau
        entries[lat]["lvl"] = int(lvl)
        continue
    t = tips.get(lat)
    entries[lat] = {"lat": lat, "fr": fr, "fam": fam, "type": typ, "orig": orig, "lvl": int(lvl),
                    "tip": t["tip"] if t else "", "diff": t["diff"] if t else "", "conf_lat": t["conf"] if t else []}

catalog, missing_tips, rejected, seen_keys = [], [], [], {}
for lat, e in entries.items():
    if lat in EXCLUDE:
        continue
    m = index.get(lat) or {}
    org = m.get("organs", {})
    key = m.get("key")
    n = {o: len(org.get(o, [])) for o in ("leaf", "flower", "fruit", "bark", "habit")}
    fruit_slot = "fruit" if n["fruit"] else ("flower" if n["flower"] else None)
    if not (key and n["leaf"] and fruit_slot and n["bark"] and n["habit"]):
        rejected.append((lat, n))
        continue
    if key in seen_keys:  # synonymes : une seule fiche par espèce
        continue
    seen_keys[key] = lat
    if not e.get("tip"):
        missing_tips.append(lat)
        continue
    e = dict(e)
    e["id"] = e.get("id") or slug(lat)
    e["slots"] = {"leaf": "leaf", "fruit": fruit_slot, "bark": "bark", "habit": "habit"}
    catalog.append(e)

# Plantes de pépinière dont les photos ont été choisies à la main sur iNaturalist (tools/curate_inat.py)
picks_path = os.path.join(ROOT, "data/curated_picks.json")
picks = json.load(open(picks_path)) if os.path.exists(picks_path) else {}
have = {e["lat"] for e in catalog}
for lat, pk in picks.items():
    if lat in have or lat in EXCLUDE or lat not in entries or not entries[lat].get("tip"):
        continue
    e = dict(entries[lat])
    e["id"] = e.get("id") or slug(lat)
    e["slots"] = {k: (v[1] if isinstance(v, list) else k) for k, v in pk.items()}
    e["curated"] = True
    catalog.append(e)
print("ajoutées à la main (iNaturalist) :", sum(1 for e in catalog if e.get("curated")))

lat2id = {e["lat"]: e["id"] for e in catalog}
for e in catalog:
    e["conf"] = [lat2id[c] for c in e.pop("conf_lat", []) if c in lat2id and lat2id[c] != e["id"]]
catalog.sort(key=lambda e: (e["lvl"], e["fr"]))
json.dump(catalog, open(os.path.join(ROOT, "data/catalog.json"), "w"), ensure_ascii=False, indent=1)

from collections import Counter
print(len(catalog), "plantes retenues", dict(sorted(Counter(e["lvl"] for e in catalog).items())))
print("fruit remplacé par la fleur :", sum(1 for e in catalog if e["slots"].get("fruit") == "flower"))
print("sans conseil :", len(missing_tips), missing_tips)
print("rejetées (photos manquantes) :", len(rejected))
for lat, n in rejected:
    print("   ", lat, n)
