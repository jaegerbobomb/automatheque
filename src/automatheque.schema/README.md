# automatheque.schema

Domaine pour des classes courantes et partagées

Objectifs :

* partager des structures de données
* metadonnées ou etiquettes et adaptateurs faciles

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
