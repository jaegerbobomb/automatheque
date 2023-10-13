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
