# -*- coding: utf-8 -*-
"""Exceptions propres au renommage.

Elles héritent de :class:`automatheque.exceptions.AutomathequeBaseException`
afin que le code appelant puisse filtrer d'un seul `except` toutes les
exceptions de l'automathèque.
"""

from automatheque.exceptions import AutomathequeBaseException


class RenommageEchec(AutomathequeBaseException):
    """Le renommage n'a pas abouti."""

    def __init__(self, msg="Renommage échoué."):
        """Initialisation."""
        self.msg = msg
        super().__init__(self.msg)


class AucunGabaritApplicable(RenommageEchec, ValueError):
    """Aucun gabarit ne s'applique à l'objet à renommer.

    Hérite aussi de :class:`ValueError`, que levait le code d'origine : un
    appelant qui l'attrapait continue de fonctionner.
    """

    def __init__(self, msg="Aucun gabarit applicable."):
        """Initialisation."""
        super().__init__(msg)


class GabaritInapplicable(RenommageEchec, ValueError):
    """Le gabarit choisi n'a pas pu produire un nom de fichier.

    En pratique : son squelette référence un champ que l'objet ne fournit pas.
    """

    def __init__(self, squelette, raison=""):
        """Initialisation."""
        self.squelette = squelette
        super().__init__(
            "Le squelette '{}' n'a pas pu être formaté. {}".format(squelette, raison)
        )


class ConditionInvalide(RenommageEchec, ValueError):
    """La condition d'un gabarit n'est pas une expression évaluable.

    Soit elle est mal formée, soit elle contient autre chose que des
    littéraux, des opérateurs booléens et des comparaisons.
    """

    def __init__(self, condition, raison=""):
        """Initialisation."""
        self.condition = condition
        super().__init__("Condition invalide : '{}'. {}".format(condition, raison))


class CibleHorsRepertoire(RenommageEchec, ValueError):
    """Le chemin construit sort du répertoire cible demandé.

    Garde-fou de dernier recours : les champs qui alimentent un squelette sont
    déjà assainis un par un. Si malgré cela le chemin s'échappe — un squelette
    absolu, une combinaison inattendue — le déplacement est refusé plutôt que
    d'écrire ailleurs que là où l'appelant l'a demandé.
    """

    def __init__(self, cible, rep_cible):
        """Initialisation."""
        self.cible = cible
        self.rep_cible = rep_cible
        super().__init__(
            "La cible '{}' sort du répertoire '{}'.".format(cible, rep_cible)
        )


class TransfertIncomplet(RenommageEchec):
    """La copie vers la cible n'a pas produit un fichier identique.

    L'original est conservé : le supprimer perdrait des données.
    """

    def __init__(self, source, cible):
        """Initialisation."""
        self.source = source
        self.cible = cible
        super().__init__(
            "Les deux fichiers sont différents {} -> {}".format(source, cible)
        )
