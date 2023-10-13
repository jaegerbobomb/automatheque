# -*- coding: utf-8 -*-
"""Module pour le patron Borg.

Spécifique à python, ce patron a le même but que le patron Singleton, mais au lieu de
forcer l'existence d'une unique instance d'une classe, le patron Borg permet d'avoir
plusieurs instances mais qui partagent le même état.

[wikipedia](https://fr.wikipedia.org/wiki/Singleton_(patron_de_conception)#Consid%C3%A9rations_avanc%C3%A9es)

source: https://github.com/faif/python-patterns/blob/master/patterns/creational/borg.py
"""


class Borg:
    """Classe "Singleton-like" pour partager les états de plusieurs instances."""

    # variable de classe contenant l'état à partager
    __etat_partage = {}

    def __init__(self):
        # copie de l'état lors de l'initialisation d'une nouvelle instance
        self.__dict__ = self.__etat_partage

