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


class CapaciteNonRendue(AutomathequeBaseException, TypeError):
    """Un greffon déclare une capacité qu'il n'implémente pas (``greffon``, #1).

    Levée à la **définition de la classe** : déclarer une capacité engage à en
    fournir les membres, sans quoi l'appelant qui obtient le greffon par
    :meth:`~automatheque.greffon.registre.RegistreGreffons.greffons_par_capacite`
    se heurte à un ``AttributeError`` opaque, loin de la cause.

    Hérite aussi de :class:`TypeError` : une classe qui ne satisfait pas
    l'interface annoncée est, dans l'esprit de la stdlib (méthodes abstraites
    non implémentées), une erreur de type.
    """

    def __init__(self, greffon, capacite, membres=()):
        """:param greffon: la classe fautive. :param capacite: capacité
        déclarée. :param membres: les membres exigés qui manquent."""
        self.greffon = getattr(greffon, "__name__", greffon)
        self.capacite = getattr(capacite, "__name__", capacite)
        self.membres = tuple(membres)
        self.msg = (
            "{} déclare la capacité {} mais n'implémente pas : {}. Retirez-la "
            "de CAPACITES ou fournissez le(s) membre(s) manquant(s).".format(
                self.greffon, self.capacite, ", ".join(self.membres)
            )
        )
        super().__init__(self.msg)


class LangueInconnue(AutomathequeBaseException, LookupError):
    """Code de langue non résolu par le registre (``util/langues.py``, #136).

    Levée par :func:`automatheque.util.langues.resout_langue` quand un code
    (« de », « es »…) n'est déclaré par aucun point d'entrée du groupe
    ``automatheque.langues``. Le message **nomme** ce qu'il faut installer —
    même esprit que l'``ImportError`` d'un extra manquant — plutôt qu'un
    ``None`` ou un ``KeyError`` nu.

    Hérite aussi de :class:`LookupError` (la famille de ``KeyError``) : une
    langue absente du registre est, dans l'esprit de la stdlib, une clé
    introuvable.
    """

    def __init__(self, code, disponibles=()):
        """:param code: le code demandé. :param disponibles: codes connus."""
        self.code = code
        self.disponibles = tuple(disponibles)
        dispo = ", ".join(self.disponibles) if self.disponibles else "aucune"
        self.msg = (
            "Langue {!r} inconnue (disponibles : {}). Installez un paquet qui "
            "la déclare dans le groupe de points d'entrée 'automatheque.langues', "
            "ou passez directement un objet Langue.".format(code, dispo)
        )
        super().__init__(self.msg)
