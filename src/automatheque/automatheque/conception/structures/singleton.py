# -*- coding: utf-8 -*-
"""Module pour le patron Singleton.

Ce patron vise à assurer qu'il n'y a toujours qu'une seule instance d'une classe en
fournissant une interface pour la manipuler. C'est un des patrons les plus simples.

L'objet qui ne doit exister qu'en une seule instance comporte une méthode pour obtenir
cette unique instance et un mécanisme pour empêcher la création d'autres instances.
Mais en python ce n'est pas nécessaire, la variable de classe "cls.instance" suffit.

[wikipedia](https://fr.wikipedia.org/wiki/Singleton_(patron_de_conception))

NB: ! attention il s'agit d'un "antipattern"
"""


class Singleton(object):
    """Classe Singleton qui permet l'héritage."""

    # Dictionnaire Python référençant les instances déjà créés : une pour chaque
    # sous-classe.
    _singletons = {}

    def __new__(cls, *args, **kargs):
        if Singleton._singletons.get(cls) is None:
            Singleton._singletons[cls] = object.__new__(cls, *args, **kargs)
        return Singleton._singletons[cls]
