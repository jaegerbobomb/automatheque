# -*- coding: utf-8 -*-
"""Module pour le patron Monteur.

Ce patron sépare le processus de construction d'un objet de sa représentation. Cela
permet d'utiliser le même processus pour obtenir différents résultats.

Dans les faits une classe délègue la création de ses instances à un Monteur, mais garde
le contrôle sur le processus de création.

Ainsi il faut créer des Monteurs "concrets" (sous-classe) pour chaque représentation
différente, qui respectent l'interface de montage de la classe exigée.

Ce patron est particulièrement utile quand il y a de nombreux paramètres de création,
presque tous optionnels.
"""


class Monteur(object):
    """Classe abstraite pour le patron Monteur.

    Cela permet d'avoir plusieurs filles du constructeur différentes pour générer les
    instances différemment ou renvoyer des instances de classes différentes étant
    donné les arguments en entrée du monteur.

    Le processus de création est par défaut défini dans :Monteur.construit:
    """

    CLASSE = None

    def __call__(self, *args, **kwargs):
        """Facilite la construction des objets."""
        return self.construit(*args, **kwargs)

    def construit(self, *args, **kwargs):
        """Fonction à surcharger par les Monteurs concrets.

        Par défaut cela renvoie juste une instance de la classe self.CLASSE.
        """
        if self.CLASSE is None:
            raise NotImplementedError
        return self.CLASSE()
