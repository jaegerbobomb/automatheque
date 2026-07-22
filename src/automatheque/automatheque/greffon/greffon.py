# -*- coding=utf-8 -*-
"""Gestion des Greffons et de leur capacités."""

import functools
import logging
import time
import uuid
from typing import List, Type

import attr

from automatheque.configuration import charge_configuration
from automatheque.greffon.capacite import Capacite
from automatheque.greffon.registre import RegistreGreffons
from automatheque.util.classe import classproperty

LOGGER = logging.getLogger(__name__)


def signale_appel(methode):
    """Décorateur journalisant l'appel d'une méthode de **capacité** d'un Greffon.

    À poser sur les méthodes qui implémentent une :class:`Capacite`. Journalise
    (niveau ``DEBUG``) le début et la fin de l'appel — avec sa durée — préfixés
    par l'identité du greffon (``cle||identifiant``). En cas d'exception,
    journalise l'échec (niveau ``ERROR``, avec la trace) **puis la propage** :
    le décorateur n'avale aucune erreur.

    .. code-block:: python

       class LecteurGreffon(Greffon):
           CAPACITES = [LireCapacite]

           @signale_appel
           def lire(self) -> bool:
               ...
    """

    @functools.wraps(methode)
    def _enveloppe(self, *args, **kwargs):
        self._signale_appel(methode.__name__)
        debut = time.monotonic()
        try:
            resultat = methode(self, *args, **kwargs)
        except Exception:
            LOGGER.exception(
                "Greffon %s||%s - échec de l'appel « %s »",
                self.cle,
                self.identifiant,
                methode.__name__,
            )
            raise
        self._signale_fin_appel(methode.__name__, time.monotonic() - debut)
        return resultat

    return _enveloppe


@attr.s(eq=False)  # pour rendre la classe hashable pour le set du registre
class Greffon(RegistreGreffons):
    """
    https://fr.wikipedia.org/wiki/Plugin : on utilise "greffon" au lieu de
    "module d'extension" car c'est plus compact et moins prône à la confusion,
    malgré la recommandation de la DGLFLF.

    ## Pourquoi utiliser des greffons :

    * "Donner accès, pour une même fonction, à différentes solutions" :
        * = pouvoir modifier le comportement de l'application, notamment en
          fonction de la conf
        * ex: pour récupérer les données nutritionnelles d'un aliment, je peux
          utiliser l'api API1 grâce au greffon adéquat, ou l'api API2 via son
          greffon, et je décide en configuration laquelle il faut utiliser et
          quels arguments pour chaque greffon (login etc.), les 2 greffons
          partageant les mêmes "capacités"
    * Peut évoluer plus vite, car il est plus simple de créer un nouveau greffon
    pour une nouvelle interface (pour une nouvelle api par exemple, ou un nouveau
    site de données, ou un nouveau traitement) que d'attendre une nouvelle version
    du logiciel.

    ## Quel greffon récupérer :

    * un par un, par le biais du nom du greffon
        * si on veut un traitement spécifique, ex: je veux utiliser l'api
          openfoodfacts, ou bien je veux parser un fichier qif vs un fichier
          csv ...)
    * tous ceux qui rendent un service donné :
        * on exécute le premier qui marche
            * ex: j'utilise la capacité "ALIMENT.PEUPLER_INFOS_NUTRITIONNELLES",
              et je m'arrête après le premier appel OK
        * ou un accumule les données (idem mais je complète les données à chaque
          appel d'un nouveau greffon)
        * NB le choix entre ces 2 manières de fonctionner dépend du logiciel qui
          utilise les greffons, ici automatheque se contente de les rendre
          accessibles et recherchables.
    """

    # Utilisation de kw_only=True pour l'héritage :
    # https://github.com/python-attrs/attrs/issues/38
    # Il faut utiliser l'option également dans les classes filles.
    identifiant = attr.ib(factory=lambda: str(uuid.uuid4()), kw_only=True)
    config_requise = attr.ib(default=False, init=False, kw_only=True)
    config = attr.ib(init=False, factory=charge_configuration, kw_only=True)

    # Liste des capacités du greffon, surchargée par chaque sous-classe
    # (cf. greffon/capacite.py) ; vide par défaut.
    CAPACITES: List[Capacite] = []

    @classproperty
    def cle(cls: Type["Greffon"]) -> str:
        """Retourne le nom de la classe sans "Greffon" s'il existe, en minuscule"""
        return cls.__name__.lower().replace("greffon", "")

    @property
    def capacites(self) -> List[Capacite]:
        return self.CAPACITES

    @property
    def actif(self) -> bool:
        """Renvoie True si le Greffon peut fonctionner sans configuration

        ou s'il nécessite une configuration mais que celle ci est bien chargée.
        """
        if not self.config_requise or self.config:
            return True
        return False

    def _signale_appel(self, nom_appel=None):
        """Journalise le **début** d'un appel de capacité (cf. `signale_appel`)."""
        suffixe = f" « {nom_appel} »" if nom_appel else ""
        LOGGER.debug(
            "Greffon %s||%s - début appel%s", self.cle, self.identifiant, suffixe
        )

    def _signale_fin_appel(self, nom_appel=None, duree=None):
        """Journalise la **fin** d'un appel de capacité (cf. `signale_appel`)."""
        suffixe = f" « {nom_appel} »" if nom_appel else ""
        detail = f" ({duree * 1000:.1f} ms)" if duree is not None else ""
        LOGGER.debug(
            "Greffon %s||%s - fin appel%s%s",
            self.cle,
            self.identifiant,
            suffixe,
            detail,
        )
