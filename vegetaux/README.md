# Herbier Vivant

Application d'entraînement quotidien à la reconnaissance des végétaux, pensée pour les paysagistes. Elle est entièrement en français.

- **172 végétaux** répartis en 6 niveaux, des plus communs en France aux plus difficiles, puis ceux du monde :
  1. Les incontournables
  2. Jardins et espaces verts
  3. Vivaces et graminées
  4. Les sosies (espèces faciles à confondre)
  5. Méditerranée
  6. Végétaux du monde (Japon, Amériques, Océanie, Afrique du Sud)
- Pour chaque plante : une photo, le **nom français**, le **nom latin**, la famille, l'origine, un **conseil pour la reconnaître** et un **conseil pour ne pas la confondre** avec ses sosies (avec leurs photos).
- **Séance du jour** de 10 photos, avec une série de jours consécutifs et des révisions espacées : une plante ratée revient le lendemain, une plante réussie revient après 2, 4, 8 jours…
- Un niveau se débloque quand on connaît la moitié du précédent. On peut aussi tout débloquer.
- **Herbier** : un catalogue pour consulter toutes les fiches.
- **Partager** : copie le lien ou un message d'invitation pour les amis. Chacun garde sa propre progression dans son navigateur.

## Fichiers

| Fichier | Rôle |
|---|---|
| `data/plants.json` | Les végétaux : noms, niveau, conseils, sosies |
| `data/images.json` | Photo de chaque plante (fichier Wikimedia Commons, auteur, licence) |
| `img/` | Photos (Wikimedia Commons, licences libres, crédit affiché sous chaque photo) |
| `template.html` | Code de l'application |
| `index.html` | Application prête à l'emploi (générée) |
| `tools/fetch_images.py` | Télécharge les photos depuis Wikipédia et Wikimedia Commons |
| `tools/build.py` | Génère `index.html` à partir des données |

## Ajouter une plante

1. Ajoutez une entrée dans `data/plants.json`.
2. Lancez `python3 tools/fetch_images.py`, puis `python3 tools/build.py`.

## Héberger soi-même

Le dossier peut être publié tel quel avec GitHub Pages ou n'importe quel hébergeur de pages statiques. Il suffit d'ouvrir `index.html`.
