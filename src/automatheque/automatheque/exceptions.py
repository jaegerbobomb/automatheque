# -*- coding: utf-8 -*-
"""Liste des exceptions spécifiques à automatheque."""


class AutomathequeBaseException(Exception):
    """Classe de base dont héritent les autres."""


class DependanceManquante(AutomathequeBaseException):
    """Exception levée si une dépendance est manquante."""

    def __init__(self, dependance, msg=""):
        """Initialisation."""
        self.msg = "Dépendance {} manquante. {}.".format(dependance, msg)


class ArgumentManquant(AutomathequeBaseException):
    """Exception si un argument est manquant."""

    def __init__(self, argument):
        """Initialisation."""
        self.msg = "Argument '{}' manquant.".format(argument)


class ConfigurationInvalide(AutomathequeBaseException, ValueError):
    """Configuration syntaxiquement invalide ou inexploitable.

    Hérite aussi de :class:`ValueError` : le code appelant qui attrapait
    historiquement un ``ValueError`` continue de fonctionner, tout en
    permettant désormais un filtrage spécifique via la hiérarchie
    ``AutomathequeBaseException``.
    """


class DureeInvalide(AutomathequeBaseException, ValueError):
    """Durée humaine impossible à interpréter (``util/temps.py``, #132).

    Levée quand une chaîne de durée est vide, mal formée, ou porte une unité
    inconnue — au premier rang desquelles le **mois** (``mo``, ``mois``), qu'un
    :class:`~datetime.timedelta` ne peut pas représenter et qu'on refuse donc
    plutôt que d'approximer.

    Hérite aussi de :class:`ValueError` : une durée illisible est, dans l'esprit
    de la stdlib, une valeur invalide ; le code qui attrape ``ValueError``
    continue de fonctionner tout en permettant un filtrage spécifique via la
    hiérarchie ``AutomathequeBaseException``.
    """
