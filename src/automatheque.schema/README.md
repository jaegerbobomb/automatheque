# automatheque.schema

Domaine pour des classes courantes et partagées

Objectifs :

* partager des structures de données
* metadonnées ou etiquettes et adaptateurs faciles

## Les familles

Le paquet est découpé par famille de média, comme l'était l'ancien `modele/` :

| Espace | Contenu |
|---|---|
| `schema.texte` | `Courriel` |
| `schema.geolocalisation` | `Emplacement` — une position GPS et/ou une adresse |
| `schema.calendrier` | `Evenement` — ce qui a eu lieu, quand, et où |

`schema.video` et `schema.audio` viendront s'y ajouter.

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

## TODO

donner des exemples pour l'héritage de renommable etc. qu'on ne va plus intégrer ici

=> encourager le sous classage :

```py
class ChansonRenommable(Chanson, Renommable):
    def liste_champs():
        pass

    def gabarits():
        pass
```

## Requirement

Python >=3.8

## Installation

```bash
pip install automatheque.schema
```

## License

GPLv3.0
