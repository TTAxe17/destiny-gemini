"""Inventaire des photos de saison (Pl@ntNet via GBIF), hémisphère Nord uniquement.

Pour chaque plante du catalogue, cherche des photos datées :
  spring_flower  fleur, de mars à mai
  autumn_leaf    feuillage, de septembre à novembre (couleurs d'automne)
  winter_habit   port / silhouette, de décembre à février
et, pour remplacer les photos faibles, d'autres candidates :
  more_leaf (mai-septembre), more_fruit (juillet-novembre), more_habit (toute l'année), more_bark
Sortie : data/season_index.json (reprend là où il s'est arrêté)
"""
import json, os, threading, time, urllib.parse, urllib.request, urllib.error
from concurrent.futures import ThreadPoolExecutor

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
UA = "PlantQuizBuilder/1.0 (educational, low-volume)"
DATASETS = ["7a3679ef-5582-4aaa-81f0-8c2545cafc81", "14d5676a-2c54-4f94-9023-1e8dcd822aa0"]
KEEP = 20
QUERIES = {   # nom : (organe, mois)
    "spring_flower": ("flower", "3,5"),
    "autumn_leaf": ("leaf", "9,11"),
    "winter_habit": ("habit", "12"),      # décembre, puis janvier-février ci-dessous
    # (candidates supplémentaires pour les photos faibles : voir tools/improve_photos.py)
}

catalog = json.load(open(os.path.join(ROOT, "data/catalog.json")))
media = json.load(open(os.path.join(ROOT, "data/media_index.json")))
out_path = os.path.join(ROOT, "data/season_index.json")
index = json.load(open(out_path)) if os.path.exists(out_path) else {}
lock = threading.Lock()


def get(url):
    for attempt in range(6):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=60) as r:
                d = json.loads(r.read())
            time.sleep(0.25)
            return d
        except urllib.error.HTTPError as e:
            if e.code in (429, 500, 502, 503, 504):
                time.sleep(10 * (attempt + 1)); continue
            return None
        except Exception:
            time.sleep(10 * (attempt + 1))
    return None


def search(key, organ, months, skip):
    found, seen = [], set(skip)
    month_sets = [months] if months != "12" else ["12", "1,2"]
    for ds in DATASETS:
        for m in month_sets:
            for page in range(1):
                params = {"taxonKey": key, "datasetKey": ds, "mediaType": "StillImage", "limit": 300,
                          "offset": page * 300, "decimalLatitude": "35,72"}
                if m:
                    params["month"] = m
                d = get("https://api.gbif.org/v1/occurrence/search?" + urllib.parse.urlencode(params))
                if not d:
                    break
                for r in d.get("results", []):
                    for md in r.get("media", []):
                        t = md.get("title") or ""
                        o = t.rsplit(":", 1)[-1].strip().lower() if ":" in t else ""
                        url = md.get("identifier") or ""
                        if o != organ or not url or url in seen:
                            continue
                        seen.add(url)
                        found.append({"url": url, "by": md.get("creator") or md.get("rightsHolder") or "",
                                      "lic": (md.get("license") or "").split("(")[-1].rstrip(")") or "cc-by-sa",
                                      "src": md.get("source") or "", "month": r.get("month")})
                if len(found) >= KEEP or d.get("endOfRecords"):
                    break
            if len(found) >= KEEP:
                break
        if len(found) >= KEEP:
            break
    return found[:KEEP]


def work(p):
    m = media.get(p["lat"]) or {}
    key = m.get("key")
    res = {}
    if key:
        already = [c["url"] for lst in (m.get("organs") or {}).values() for c in lst]
        for name, (organ, months) in QUERIES.items():
            res[name] = search(key, organ, months, already if name.startswith("more_") else [])
    with lock:
        index[p["lat"]] = res
        n = len(index)
        print(n, p["lat"], " ".join(f"{k}={len(v)}" for k, v in res.items()), flush=True)
        if n % 20 == 0:
            json.dump(index, open(out_path, "w"))


todo = [p for p in catalog if p["lat"] not in index]
print(len(catalog), "plantes,", len(todo), "à traiter", flush=True)
with ThreadPoolExecutor(10) as ex:
    list(ex.map(work, todo))
json.dump(index, open(out_path, "w"))
print("TERMINÉ", flush=True)
