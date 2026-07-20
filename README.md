# Automathèque

**Utilitaires, modèles et librairies communes.**

[![CI](https://github.com/jaegerbobomb/automatheque/actions/workflows/ci.yml/badge.svg)](https://github.com/jaegerbobomb/automatheque/actions/workflows/ci.yml)
[![Couverture](https://img.shields.io/badge/couverture-79%25-brightgreen.svg)](https://github.com/jaegerbobomb/automatheque/actions/workflows/ci.yml)
[![Licence](https://img.shields.io/badge/licence-LGPL--3.0--or--later-blue.svg)](LICENSE)

| Paquet | Version PyPI | Python |
| --- | --- | --- |
| [`automatheque`](https://pypi.org/project/automatheque/) | [![PyPI](https://img.shields.io/pypi/v/automatheque.svg)](https://pypi.org/project/automatheque/) | ![Python](https://img.shields.io/pypi/pyversions/automatheque.svg) |
| [`automatheque.factrice`](https://pypi.org/project/automatheque.factrice/) | [![PyPI](https://img.shields.io/pypi/v/automatheque.factrice.svg)](https://pypi.org/project/automatheque.factrice/) | ![Python](https://img.shields.io/pypi/pyversions/automatheque.factrice.svg) |
| [`automatheque.schema`](https://pypi.org/project/automatheque.schema/) | [![PyPI](https://img.shields.io/pypi/v/automatheque.schema.svg)](https://pypi.org/project/automatheque.schema/) | ![Python](https://img.shields.io/pypi/pyversions/automatheque.schema.svg) |

> Le badge de couverture est un **snapshot** (mis à jour à la main). On peut le
> rendre *vivant* via Codecov si besoin — cf. PR.

## Préambule

Ce dépôt est géré en "monorepo" grâce à [monas](https://monas.fming.dev/en/latest).

Il contient la bibliothèque `automatheque` ainsi que tous les packages qui y sont liés, mais
qui sont livrés sous leur propre espace de nommage.

## Subpackage

Nous essayons dans un mono répo de gérer des sous-paquets python, pour
avoir un unique namespace "automatheque" et pouvoir publier les sous paquets "automatheque.schema" etc.

Voir (https://packaging.python.org/en/latest/guides/packaging-namespace-packages/) pour plus d'informations.

## Nomenclature que l'on essaie de respecter

D'après internet :

library
: a collection of code that is used by the applications. If you have two applications that read the mesh, then it makes more sense to put all the mesh code into a common library that they both can use, rather than duplicate that code in each application.

application
: code that can be executed from the console. Each application has a specific purpose, such as setFields, blockMesh, potentialFoam.

utility
: Utilities perform many pre and post processing tasks, such as data conversion, meshing, and geometry manipulation.

model/domain
: les classes et modèles de données génériques

En ce qui concerne la différence entre framework et librairie :

> une librairie s'adapte à votre code, alors qu'un framework vous demande d'adapter votre code !

## Remplir les ```__init__.py``` pour faciliter l'import de noms

[mike grouchy : be pythonic \_\_init__.py](http://mikegrouchy.com/blog/2012/05/be-pythonic-__init__py.html)

## Autres liens/conseils

* pour les iterators / generators / yield and co : [https://nedbatchelder.com/text/iter.html](https://nedbatchelder.com/text/iter.html)
* utiliser any , all, attritems etc.

## Licence

Copyright © dwwm93.

Automathèque est un logiciel libre distribué sous les termes de la **GNU Lesser
General Public License, version 3 ou ultérieure** (`LGPL-3.0-or-later`).

Le choix de la LGPL (copyleft *faible*) est délibéré : `automatheque` et
`automatheque.schema` sont des **bibliothèques** que l'on peut importer dans
n'importe quel projet — y compris propriétaire — sans en « contaminer » le code,
tout en garantissant que les améliorations apportées **à la bibliothèque
elle-même** restent libres.

Le texte de la LGPLv3 est dans [`LICENSE`](LICENSE) ; il complète et incorpore
la GPLv3, fournie dans [`GPL-3.0.txt`](GPL-3.0.txt). Voir aussi
[`CONTRIBUTING.md`](CONTRIBUTING.md) pour le certificat d'origine (DCO) demandé
aux contributions.
