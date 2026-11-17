"""Inventaire des photos Pl@ntNet (via GBIF) classées par organe, pour chaque candidat.

Usage : python3 tools/index_plantnet.py
Entrées : data/plants.json (fiches existantes) + data/candidates.tsv (nouveaux candidats)
Sortie  : data/media_index.json  {nom latin: {"key": taxonKey, "organs": {leaf: [...], fruit: [...], ...}}}
Reprend là où il s'est arrêté.
"""
import json, os, time, urllib.parse, urllib.request, urllib.error

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
UA = "PlantQuizBuilder/1.0 (educational, low-volume)"
DATASETS = ["7a3679ef-5582-4aaa-81f0-8c2545cafc81",   # Pl@ntNet observations (validées)
            "14d5676a-2c54-4f94-9023-1e8dcd822aa0"]   # Pl@ntNet occurrences automatiques
ORGANS = {"leaf", "flower", "fruit", "bark", "habit"}
KEEP = 14          # candidats gardés par organe
PAGES = 3          # pages de 300 occurrences max par jeu de données

out_path = os.path.join(ROOT, "data/media_index.json")
index = json.load(open(out_path)) if os.path.exists(out_path) else {}


def names():
    seen = []
    for p in json.load(open(os.path.join(ROOT, "data/plants.json"))):
        seen.append(p["lat"])
    for line in open(os.path.join(ROOT, "data/candidates.tsv")):
        if line.strip() and not line.startswith("#"):
            seen.append(line.split("|")[1].strip())
    out = []
    for n in seen:
        if n not in out:
            out.append(n)
    return out


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


def match(name):
    clean = name.replace("× ", "").replace("×", "")
    d = get("https://api.gbif.org/v1/species/match?" + urllib.parse.urlencode({"name": clean, "kingdom": "Plantae"}))
    if not d or d.get("matchType") == "NONE":
        return None
    return d.get("acceptedUsageKey") or d.get("usageKey")


def collect(key):
    organs = {o: [] for o in ORGANS}
    seen = set()
    for ds in DATASETS:
        for page in range(PAGES):
            q = urllib.parse.urlencode({"taxonKey": key, "datasetKey": ds, "mediaType": "StillImage",
                                        "limit": 300, "offset": page * 300})
            d = get("https://api.gbif.org/v1/occurrence/search?" + q)
            if not d:
                break
            for r in d.get("results", []):
                for m in r.get("media", []):
                    t = (m.get("title") or "")
                    organ = t.rsplit(":", 1)[-1].strip().lower() if ":" in t else ""
                    url = m.get("identifier") or ""
                    if organ not in ORGANS or not url or url in seen or len(organs[organ]) >= KEEP:
                        continue
                    seen.add(url)
                    organs[organ].append({"url": url, "by": m.get("creator") or m.get("rightsHolder") or "",
                                          "lic": (m.get("license") or "").split("(")[-1].rstrip(")") or "cc-by-sa",
                                          "src": m.get("source") or ""})
            if d.get("endOfRecords") or all(len(v) >= KEEP for k, v in organs.items() if k != "flower"):
                break
        if all(len(v) >= KEEP for k, v in organs.items() if k != "flower"):
            break
    return organs


from concurrent.futures import ThreadPoolExecutor
import threading
lock = threading.Lock()
done = [0]


def work(n):
    key = match(n)
    res = {"key": key, "organs": collect(key) if key else {}}
    with lock:
        index[n] = res
        done[0] += 1
        org = res["organs"]
        print(f"{done[0]} {n} : " + (" ".join(f"{k}={len(v)}" for k, v in sorted(org.items())) if key else "introuvable"), flush=True)
        if done[0] % 20 == 0:
            json.dump(index, open(out_path, "w"))


all_names = names()
todo = [n for n in all_names if n not in index]
print(len(all_names), "candidats,", len(todo), "à traiter", flush=True)
with ThreadPoolExecutor(4) as ex:
    list(ex.map(work, todo))
json.dump(index, open(out_path, "w"))
full = [n for n, v in index.items() if all(len(v["organs"].get(o, [])) >= 1 for o in ("leaf", "fruit", "bark", "habit"))]
print("TERMINÉ.", len(full), "plantes avec feuille + fruit + écorce + port", flush=True)
