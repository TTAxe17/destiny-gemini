# Herbier Vivant

Application d'entraînement quotidien à la reconnaissance des végétaux, pensée pour les paysagistes. Elle est entièrement en français.

- **172 végétaux** répartis en 6 niveaux, des plus communs en France aux plus difficiles, puis ceux du monde :
  1. Les incontournables
  2. Jardins et espaces verts
  3. Vivaces et graminées
  4. Les sosies (espèces faciles à confondre)
  5. Méditerranée
  6. Végétaux du monde (Japon, Amériques, Océanie, Afrique du Sud)
- Pour chaque plante : 3 photos (une au hasard à chaque question, les autres dans la fiche), le **nom français**, le **nom latin**, la famille, l'origine, un **conseil pour la reconnaître** et un **conseil pour ne pas la confondre** avec ses sosies (avec leurs photos).
- **Séance du jour** de 10 photos, avec une série de jours consécutifs et des révisions espacées : une plante ratée revient le lendemain, une plante réussie revient après 2, 4, 8 jours…
- Un niveau se débloque quand on connaît la moitié du précédent. On peut aussi tout débloquer.
- **Herbier** : un catalogue pour consulter toutes les fiches.
- **Partager** : copie le lien ou un message d'invitation pour les amis. Chacun garde sa propre progression dans son navigateur.

## Fichiers

| Fichier | Rôle |
|---|---|
| `data/plants.json` | Les végétaux : noms, niveau, conseils, sosies |
| `data/photos.json` | Photos de chaque plante (auteur, licence, lien iNaturalist) |
| `img/` | Photos iNaturalist sous licences Creative Commons, crédit affiché sous chaque photo |
| `template.html` | Code de l'application |
| `index.html` | Application prête à l'emploi (générée) |
| `tools/fetch_inat.py` | Télécharge les photos depuis iNaturalist |
| `tools/build.py` | Génère `index.html` à partir des données |

## Ajouter une plante

1. Ajoutez une entrée dans `data/plants.json`.
2. Lancez `python3 tools/fetch_inat.py`, puis `python3 tools/build.py`.

## En ligne

Version publiée : https://claude.ai/artifact/VKobStoCcmh9hH27HKrAtF

## Installer sur son téléphone

Hébergée sur GitHub Pages (ou tout hébergement HTTPS), l'application s'installe comme une appli :

- **iPhone (Safari)** : bouton Partager, puis « Sur l'écran d'accueil ».
- **Android (Chrome)** : menu ⋮, puis « Installer l'application » ou « Ajouter à l'écran d'accueil ».

Elle s'ouvre alors en plein écran avec son icône, et fonctionne hors connexion : les photos sont gardées sur le téléphone après la première ouverture.

## Héberger soi-même

Activez GitHub Pages sur la branche (Settings → Pages → Deploy from a branch, dossier `/ (root)`), puis ouvrez `https://<utilisateur>.github.io/<dépôt>/vegetaux/`.
Les fichiers `manifest.webmanifest`, `sw.js` et les icônes rendent l'application installable.
