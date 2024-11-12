from abc import ABC, ABCMeta
from copy import deepcopy
from typing import List, Optional, Union

from automatheque.conception.structures import Fabrique, Monteur
from automatheque.configuration import ConfigParser, charge_configuration
from automatheque.greffon.greffon import Greffon
from automatheque.greffon.registre import MetaInstancePersistanteRegistre
from automatheque.log import recup_logger

LOGGER = recup_logger(__name__)


class FabriqueGreffon(Fabrique):
    """Classe qui permet d'instancier les Greffons dont les Monteur ont été enregistrés.

    Il faut :

    1. enregistrer les monteurs des greffons avec `fabrique_greffons.charge_monteurs()`
    2. instancier le type de greffon demandé, via `fabrique_greffons.active()`, qui lance
       `monteur.cree()` avec les arguments donnés, pour instancier le Greffon.

    NB : À défaut de Monteur, s'il n'y a pas de complexité pour instancier un Greffon (en
    particulier il n'y a pas plusieurs Greffons différents à instancier en fonction de la
    configuration utilisateur), alors on peut donner la classe du Greffon en tant que
    monteur et celle ci sera instanciée directement.
        Attention: pour que la classe Greffon se comporte comme un monteur, il faut
        qu'elle ait une propriété "clé".

    NB: Si on utilise un Monteur, on peut utiliser la même clé que le Greffon, tant qu'elle
    n'est pas utilisée par plusieurs Greffons ou Monteurs, puisqu'elle servira à
    déclencher l'instanciation du Monteur ou du Greffon associée.

    .. code-block:: python
        >>> from automatheque.greffon import fabrique_greffon
        >>> from plugin2.monteur import Monteur2  # dépend de l'argument donné à `charge_monteurs`
        >>> fabrique_greffon.charge_monteurs([
               "plugin1.monteur.Monteur1",
               Monteur2
            ])
        >>> plugin1_id1 = fabrique_greffon.active(
               "monteur1",
               *args,
               identifiant="plugin1_identifiant1",
               **kwargs
            )
        >>> plugin1_id1.appel_quelconque_capacite()
    """

    def active(
        self, cle_monteur, *args, identifiant=None, **kwargs
    ) -> Union[Greffon, False, None]:
        """Va chercher dans le registre des greffons et renvoie le greffon activé.

        S'il ne trouve pas le greffon grâce à l'identifiant donné, alors il en
        instancie un nouveau.
        En l'absence d'identifiant, un nouveau Greffon est instancié et on lui
        attribue un identifiant unique auto-généré.
        """
        if not identifiant or identifiant not in Greffon.greffons_identifiants():
            try:
                if identifiant:
                    kwargs["identifiant"] = identifiant
                instance_greffon = self.cree(cle_monteur, *args, **kwargs)
                LOGGER.debug(f"Greffon instancié : {instance_greffon}")
                if not instance_greffon.actif:
                    LOGGER.warning(f"Greffon {instance_greffon} inactif")
                    return False
                identifiant = instance_greffon.identifiant
            except Exception:
                LOGGER.exception(
                    f"Echec activation greffon : {identifiant} de type {cle_monteur}"
                )
        return Greffon.greffon_par_identifiant(identifiant)

    def charge_monteurs(
        self, liste_monteurs: List[Union[str, Monteur, Greffon]]
    ) -> List[Monteur]:
        """Enregistre les monteurs de greffons disponibles dans la fabrique.

        Cela  pourrait etre fait de manière automatique, par ex en scannant un
        répertoire.
        Dans tous les cas ensuite il faut les activer un par un dans la configuration.
        """
        monteurs = []
        for elem in liste_monteurs:
            if isinstance(elem, str):
                from pydoc import locate

                monteur = locate(elem)  # ou importlib TODO ?
            else:
                monteur = elem
            if issubclass(monteur, Greffon):
                monteur_concret = monteur
            elif issubclass(monteur, Monteur):
                monteur_concret = monteur()  # Il faut instancier le Monteur
            else:
                raise ValueError(
                    "La fabrique ne peut charger que des Greffons ou des Monteurs"
                )
            monteurs.append(self.enregistre_monteur(monteur.cle, monteur_concret))
        return monteurs

    # def greffons_charge_defaut(self):
    #    """Charge les greffons par défaut dans la liste de monteurs."""
    #    self.enregistre_greffons(LISTE_GREFFONS_DEFAUT)
    #    LOGGER.debug(f"Greffons chargés : {self.recup_monteurs()}")

    def active_greffons_conf(
        self,
        liste_greffons: Optional[List[str]] = None,
        configuration: Union[dict, ConfigParser, None] = None,
    ) -> List[Greffon]:
        """Active les greffons qui sont définis en conf dans l'option "greffons".

        Si liste_greffons est remplie, on ne charge que ces identifiants-ci et pas
        tous ceux définis en configuration.

        Si on utilise cette méthode pour activer les greffons, alors il est nécessaire
        de fournir un identifiant, on ne peut pas laisser automatheque créer l'identifiant
        automatiquement, donc il faut fournir une configuration ou laisser automatheque
        charger la configuration standard.

        configuration peut donc être un dictionnaire ou un ConfigParser de la
        configuration`.ini` suivante :

        .. code-block:: ini
            [greffons]
            # liste d'identifiants des greffons, il peut y avoir plusieurs identifiants
            # pour le même greffon, par exemple avec des arguments différents
            greffons=kodi1,kodi2,trakt1

            [kodi1]
            # clé du monteur ou du plugin
            greffon=kodi
            # Argument supplémentaire fourni à l'instanciation
            hote=xxx
            [kodi2]
            # clé du monteur ou du plugin
            greffon=kodi
            # Argument supplémentaire fourni à l'instanciation
            hote=yyy
            [trakt1]
            greffon=trakt

        """
        if configuration is None:
            configuration = dict(charge_configuration())
        elif isinstance(configuration, ConfigParser):
            configuration = dict(configuration)
        elif not isinstance(configuration, dict):
            raise ValueError("'configuration' n'est pas au bon format")

        if liste_greffons is None:
            try:
                # On laisse dans "greffon" si on veut sortir le code un jour !
                liste_greffons = configuration.get("greffons").get("greffons")
                liste_greffons = [i.strip() for i in liste_greffons.split(",")]
            except Exception as e:
                LOGGER.exception(e)
                raise ValueError(f"pas de liste de greffons dans {configuration}")

        greffons_actifs = []
        for identifiant in liste_greffons:
            conf = deepcopy(configuration.get(identifiant))
            cle = conf.pop("greffon")
            greffons_actifs.append(self.active(cle, identifiant=identifiant, **conf))
        return greffons_actifs


class MetaABCGreffon(ABCMeta, MetaInstancePersistanteRegistre):
    """Metaclass à utiliser pour créer un Greffon abstrait.

    .. code-block:: python

        class GreffonAbstrait(ABC, Greffon, metaclass=MetaABCGreffon):
            @abstractmethod
            def test(self):
                pass
    """

    pass


class GreffonAbstrait(ABC, Greffon, metaclass=MetaABCGreffon):
    """Greffon abstrait à sous-classer directement.

    .. code-block:: python

        from abc import abstractmethod

        class GreffonQuelconqueInterface(GreffonAbstrait):
            @abstractmethod
            def methode_importante(self):
                raise NotImplementedError
    """

    pass


fabrique_greffon = FabriqueGreffon()
