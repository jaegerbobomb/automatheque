# Automathèque

**Utilitaires, modèles et librairies communes.**

## Préambule

Ce dépôt est géré en "monorepo" grâce à [monas](https://monas.fming.dev/en/latest).

Il contient la bibliothèque `automatheque` ainsi que tous les packages qui y sont liés, mais
qui sont livrés sous leur propre espace de nommage.

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
