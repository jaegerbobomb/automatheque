# -*- coding=utf-8 -*-
"""Gestion des Greffons et de leur capacités.
"""
import uuid

import attr

from automatheque.configuration import charge_configuration
from automatheque.greffon.registre import RegistreGreffons
from automatheque.log import recup_logger
from automatheque.util.classe import classproperty


LOGGER = recup_logger(__name__)
LOGGER.debug("LOGGER")


@attr.s(eq=False)  # pour rendre la classe hashable pour le set du registre
class Greffon(RegistreGreffons):
    """
    https://fr.wikipedia.org/wiki/Plugin : on utilise "greffon" au lieu de "module d'extension" car
    c'est plus compact et moins prône à la confusion, malgré la recommandation de la DGLFLF.

    ## Pourquoi utiliser des greffons :

    * "Donner accès, pour une même fonction, à différentes solutions" :
        * = pouvoir modifier le comportement de l'application, notamment en fonction de la conf
        * ex: pour récupérer les données nutritionnelles d'un aliment, je peux utiliser l'api API1
        grâce au greffon adéquat, ou l'api API2 via son greffon, et je décide en configuration
        laquelle il faut utiliser et quels arguments pour chaque greffon (login etc.), les 2
        greffons partageant les mêmes "capacités"
    * Peut évoluer plus vite, car il est plus simple de créer un nouveau greffon pour une nouvelle
    interface (pour une nouvelle api par exemple, ou un nouveau site de données, ou un nouveau
    traitement) que d'attendre une nouvelle version du logiciel.

    ## Quel greffon récupérer :

    * un par un, par le biais du nom du greffon
        * si on veut un traitement spécifique, ex: je veux utiliser l'api openfoodfacts, ou bien je
          veux parser un fichier qif vs un fichier csv ...)
    * tous ceux qui rendent un service donné :
        * on exécute le premier qui marche
            * ex: j'utilise la capacité "ALIMENT.PEUPLER_INFOS_NUTRITIONNELLES", et je m'arrête
              après le premier appel OK
        * ou un accumule les données (idem mais je complète les données à chaque appel d'un nouveau
          greffon)
        * NB le choix entre ces 2 manières de fonctionner dépend du logiciel qui utilise les
          greffons, ici automatheque se contente de les rendre accessibles et recherchables.
    """

    # Utilisation de kw_only=True pour l'héritage :
    # https://github.com/python-attrs/attrs/issues/38
    # Il faut utiliser l'option également dans les classes filles.
    identifiant = attr.ib(default=str(uuid.uuid4()), kw_only=True)
    config_requise = attr.ib(default=False, init=False, kw_only=True)
    config = attr.ib(init=False, factory=charge_configuration, kw_only=True)

    @classproperty
    def cle(cls):
        """Retourne le nom de la classe sans "Greffon" s'il existe, en minuscule"""
        return cls.__name__.lower().replace("greffon", "")

    @property
    def capacites(self):
        return self.CAPACITES

    @property
    def actif(self):
        """TODO pas très clair le fonctionnement !"""
        if not self.config_requise or self.config:
            return True
        return False

    def _signale_appel(self):
        # TODO log !!!
        # TODO on devrait mettre une annotation sur tous les appels de type "capacites"
        LOGGER.debug("Greffon : {} - debut appel".format(self.cle))
