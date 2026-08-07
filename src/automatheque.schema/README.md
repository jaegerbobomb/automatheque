# automatheque.schema

Domaine pour des classes courantes et partagées

Objectifs :

* partager des structures de données
* metadonnées ou etiquettes et adaptateurs faciles

## Les familles

Le paquet est découpé par famille de média, comme l'était l'ancien `modele/` :

| Espace | Contenu |
|---|---|
| `schema.media` | `Media` — le socle commun aux familles |
| `schema.texte` | `Courriel` |
| `schema.image` | `BaseTags` (les étiquettes d'une image), `Photo` |
| `schema.geolocalisation` | `Emplacement` — une position GPS et/ou une adresse |
| `schema.calendrier` | `Evenement` — ce qui a eu lieu, quand, et où |

`schema.video` et `schema.audio` viendront s'y ajouter. `schema.media` est
réservé à ce qui est **commun** aux familles.

## Ce qui entre ici, et ce qui n'y entre pas

`schema` est le **vocabulaire** : ce que les choses *sont*, pour circuler
d'une application à l'autre. Trois règles en découlent.

* **Des structures pures.** Des classes `attrs`, aucune entrée/sortie, aucune
  expression rationnelle. Interroger un service de géocodage, lire les EXIF
  d'un fichier, parler à un serveur CalDAV : autant d'adaptateurs, qui vivent
  ailleurs.
* **Feuille du graphe de dépendances.** `schema` ne dépend d'aucun autre
  paquet du dépôt — c'est lui qu'on consomme. Ses seules dépendances externes
  au-delà d'`attrs` sont des **extras**, réclamés à la conversion et
  facultatifs à l'installation.
* **La conversion se fait aux frontières.** `Evenement` ne *contient* pas un
  `VEVENT` iCalendar : il sait en venir et y retourner, par
  `depuis_vevent()` / `vers_vevent()`, qui n'importent `vobject` qu'à
  l'appel.

```bash
pip install "automatheque.schema[calendrier]"   # + vobject, pour l'iCalendar
```

## Réfléchir

Classe "StockageMedium" de base = classe avec un nom_fichier éventuel pour la sauvegarde ou url si dans le cloud etc.

L'idée c'est d'avoir un autre module automatheque pour gérer les xattrs , les extensions
et la sauvegarde en fichier par ex., deviner le type de media (même pour meta données ou étiquettes, qui peuvent être enregistrées dans un fichier) ...

## Sous-classage : ajouter des comportements

Les *comportements* — se renommer, se décomposer — n'entrent pas ici : ce sont
des grammaires d'application, pas du vocabulaire, et les cuire dans les classes
de schéma reviendrait à imposer à tous les consommateurs l'arborescence de
rangement d'un seul.

La classe utilisable se compose donc **chez l'appelant**, par sous-classage :

```py
from automatheque.decomposition import Decomposable
from automatheque.renommage import Gabarit, Gabarits, Renommable
from automatheque.schema.image import Photo


class PhotoRangeable(Photo, Renommable, Decomposable):
    @classmethod
    def _gabarits_par_defaut(cls):
        """L'arborescence que *cette* application veut."""
        gabarits = Gabarits()
        gabarits.append(
            Gabarit(squelette="{date:%Y}/{date:%Y-%m-%d} {album}/{nom_fichier}")
        )
        return gabarits

    def _liste_champs_dispo(self):
        """La projection des étiquettes vers les champs des gabarits."""
        return {
            "date": self.tags.date_prise_de_vue,
            "album": self.tags.album or "",
            "nom_fichier": self.basename,
        }
```

## Requirement

Python >=3.9

## Installation

```bash
pip install automatheque.schema
```

## License

LGPLv3.0 ou ultérieure
