# -*- coding: utf-8 -*-
"""Module pour le patron Fabrique.

Ce patron fournit une interface pour créer des familles d'objets sans spécifier la
classe concrète.  Le patron fabrique, ou méthode fabrique (en anglais factory ou
factory method) est un patron récurrent en génie logiciel.
Une fabrique simple retourne une instance d'une classe parmi plusieurs possibles, en
fonction des paramètres qui ont été fournis. Toutes les classes ont un lien de parenté,
et des méthodes communes, et chacune est optimisée en fonction d'une certaine donnée.

Le patron fabrique abstraite (en anglais abstract factory) va un pas plus loin que la
fabrique simple. Une fabrique abstraite est utilisée pour obtenir un jeu d'objets
connexes.
Par exemple pour implémenter une charte graphique : il existe une fabrique qui retourne
des objets (boutons, menus) dans le style de Windows, une qui retourne des objets dans
le style de Motif, et une dans le style de Macintosh. Une fabrique abstraite est obtenue
en utilisant une fabrique simple.

[wikipedia](https://fr.wikipedia.org/wiki/Fabrique_(patron_de_conception))

cf : https://realpython.com/factory-method-python/

depuis realpython ci dessus :
  The mechanics of Factory Method are always the same. A client
  (SongSerializer.serialize()) depends on a concrete implementation of an interface. It
  requests the implementation from a creator component (get_serializer()) using some
  sort of identifier (format).
"""
from .monteur import Monteur


class Fabrique(object):
    """Classe générique de base pour les "Fabriques".

    Classe pour le design pattern "Factory" pour permettre d'enregistrer les différents
    constructeurs d'objets à la volée et des renvoyer celui qui nous intéresse suivant
    l'objet que l'on souhaite construire.

    On peut
    * soit donner directement une Classe comme constructeur, et on recevra une
    instance de la classe,
    * soit un Monteur concret qui construira l'objet voulu.
     (utile par exemple si l'on veut abstraire le passage de paramètre à l'initialisation
      de la classe)
    """

    def __init__(self):
        self._monteurs = {}

    def enregistre_monteur(self, cle, monteur):
        if not isinstance(monteur, Monteur) and not callable(monteur):
            raise ValueError("Le monteur doit être 'callable'")
        self._monteurs[cle] = monteur
        return monteur

    def recup_monteurs(self):
        return self._monteurs

    def cree(self, cle, *args, **kwargs):
        """Crée l'instance dont le constructeur a la responsabilité.

        Pour les fabriques filles il est conseillé de créer un nouvelle fonction qui
        a une sémantique plus proche de ce qui est créé, et d'appeler la fonction
        Factory.cree dedans, pour rendre le code plus compréhensible.
        """
        monteur = self._monteurs.get(cle)
        if not monteur:
            raise ValueError(f"Pas de monteur {cle}")
        instance = monteur(*args, **kwargs)
        return instance
