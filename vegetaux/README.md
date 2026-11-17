# Herbier Vivant

Application d'entraînement quotidien à la reconnaissance des végétaux, pensée pour les paysagistes. Elle est entièrement en français.

- **Plus de 500 végétaux qui poussent en France**, répartis en 9 niveaux, des plus courants aux plus difficiles, puis ceux venus d'autres pays :
  1. Les incontournables
  2. Jardins et espaces verts
  3. Haies et arbustes d'ornement
  4. Arbres de parcs et d'alignement
  5. Conifères
  6. Vivaces, graminées et grimpantes
  7. Flore sauvage et sosies
  8. Méditerranée et littoral
  9. Venus d'ailleurs (espèces d'autres pays acclimatées en France)
- **4 photos à chaque question** : la feuille en détail, le fruit, l'écorce (ou la tige) et le port de la plante. Chaque photo s'agrandit en plein écran.
- Pour chaque plante : le **nom français**, le **nom latin**, la famille, l'origine, un **conseil pour la reconnaître** et un **conseil pour ne pas la confondre** avec ses sosies (avec leurs photos).
- **Séance du jour** de 10 photos, avec une série de jours consécutifs et des révisions espacées : une plante ratée revient le lendemain, une plante réussie revient après 2, 4, 8 jours…
- Un niveau se débloque quand on connaît la moitié du précédent. On peut aussi tout débloquer.
- **Herbier** : un catalogue pour consulter toutes les fiches.
- **Partager** : copie le lien ou un message d'invitation pour les amis. Chacun garde sa propre progression dans son navigateur.

## D'où viennent les photos

- **Pl@ntNet** (via GBIF) : photos d'observateurs classées par organe (feuille, fleur, fruit, écorce, port). Pour chaque organe, `tools/fetch_photos.py` examine jusqu'à 14 photos, garde celles dont les couleurs correspondent à l'organe (du vert pour une feuille, du brun ou du gris pour une écorce, du ciel pour un port), puis choisit la plus nette.
- **iNaturalist** : pour les plantes de pépinière absentes de Pl@ntNet (Photinia, Forsythia, Abélia, Choisya, Érable du Japon…), les photos ont été choisies une à une sur des planches de 16 photos (`tools/curate_inat.py`, choix dans `data/curated_picks.json`).
- Toutes les photos sont sous licence Creative Commons ; l'auteur et un lien vers l'original sont affichés sous chaque photo.

## Fichiers

| Fichier | Rôle |
|---|---|
| `data/candidates.tsv` | Liste des candidats : niveau, noms, famille, type, origine |
| `data/plants.json`, `data/tips_*.json` | Conseils de reconnaissance et sosies |
| `data/media_index.json` | Photos Pl@ntNet disponibles par organe |
| `data/catalog.json` | Catalogue final (généré) |
| `data/photo_credits.json` | Auteur, licence et source de chaque photo |
| `photos/<plante>/` | Les 4 photos de chaque plante (`leaf`, `fruit`, `bark`, `habit`) |
| `template.html` | Code de l'application |
| `index.html`, `sw.js` | Application prête à l'emploi (générées) |

## Mettre à jour

1. `python3 tools/index_plantnet.py` — inventaire des photos Pl@ntNet
2. `python3 tools/build_catalog.py` — choix des plantes
3. `python3 tools/fetch_photos.py` puis `python3 tools/curate_inat.py fetch` — photos
4. `python3 tools/build.py` — génère l'application

## Installer sur son téléphone

Hébergée sur GitHub Pages (ou tout hébergement HTTPS), l'application s'installe comme une appli :

- **iPhone (Safari)** : bouton Partager, puis « Sur l'écran d'accueil ».
- **Android (Chrome)** : menu ⋮, puis « Installer l'application » ou « Ajouter à l'écran d'accueil ».

Elle s'ouvre alors en plein écran avec son icône. Les photos vues une fois restent sur le téléphone ; l'onglet Niveaux permet aussi de télécharger d'avance celles des niveaux ouverts pour réviser sans réseau.

## Héberger soi-même

Activez GitHub Pages sur la branche (Settings → Pages → Deploy from a branch, dossier `/ (root)`), puis ouvrez `https://<utilisateur>.github.io/<dépôt>/vegetaux/`.
Les fichiers `manifest.webmanifest`, `sw.js` et les icônes rendent l'application installable.
