# -*- coding: utf-8 -*-
"""Module pour le patron Adaptateur.

Ce patron convertit l'interface d'une classe en une autre interface exploitée ailleurs.
 
Cela permet d'interconnecter des classes qui sans cela seraient incompatibles. Il est 
utilisé dans le cas où un programme se sert d'une bibliothèque de classe qui ne 
correspond plus à l'utilisation qui en est faite, à la suite d'une mise à jour de la 
bibliothèque dont l'interface a changé. 

Un objet adaptateur (en anglais adapter) expose alors l'ancienne interface en utilisant
les fonctionnalités de la nouvelle.

[wikipedia](https://fr.wikipedia.org/wiki/Adaptateur_(patron_de_conception))

source : https://github.com/faif/python-patterns/blob/master/patterns/structural/adapter.py
"""


class Adaptateur(object):
    """Remplace les méthodes d'un objet par des méthodes d'un autre objet.

    :usage:
    objet = Objet()
    objet = Adaptateur(objet, nouvelle_methode=autre_objet.methode_origine)
    objet.nouvelle_methode()  # exécute autre_objet.methode_origine()
    """

    def __init__(self, obj, **nouvelles_methodes):
        """Les méthodes sont ajoutées au dict de l'instance d'Adaptateur."""
        self.obj = obj
        self.__dict__.update(nouvelles_methodes)

    def __getattr__(self, attr):
        """Tous les appels non "adaptés" sont transmis à l'objet sous-jacent."""
        return getattr(self.obj, attr)

    def dict_originel(self):
        """Renvoie le dict originel de l'objet sous-jacent."""
        return self.obj.__dict__
