import importlib
import logging
from abc import ABC, ABCMeta
from copy import deepcopy
from importlib.metadata import entry_points
from typing import Any, List, Optional, Type, Union

from automatheque.conception.structures import Fabrique, Monteur
from automatheque.configuration import ConfigParser, charge_configuration
from automatheque.greffon.greffon import Greffon
from automatheque.greffon.greffon import signale_appel as signale_appel  # noqa: F401
from automatheque.greffon.registre import MetaInstancePersistanteRegistre

LOGGER = logging.getLogger(__name__)

# Groupe de points d'entrée où un paquet tiers déclare ses greffons.
GROUPE_GREFFONS = "automatheque.greffons"


def _resout_reference(chemin: str):
    """Résout ``"module.sousmodule.Objet"`` en l'objet référencé.

    Remplace `pydoc.locate`, qui chargeait n'importe quelle chaîne sans rien
    valider et renvoyait `None` en cas d'échec — d'où, plus loin, un
    `issubclass(None, …)` opaque. On sépare explicitement le module de
    l'attribut, on importe le module, puis on lit l'attribut, avec une erreur
    claire à chaque étape.

    :raise ValueError: si la chaîne est mal formée, le module introuvable, ou
                       l'attribut absent.
    """
    module_nom, _, attribut = chemin.rpartition(".")
    if not module_nom or not attribut:
        raise ValueError(
            f"Référence de greffon invalide : {chemin!r} (attendu 'module.Classe')"
        )
    try:
        module = importlib.import_module(module_nom)
    except ImportError as exc:
        raise ValueError(
            f"Module introuvable pour le greffon {chemin!r} : {exc}"
        ) from exc
    try:
        return getattr(module, attribut)
    except AttributeError as exc:
        raise ValueError(
            f"{attribut!r} absent du module {module_nom!r} (greffon {chemin!r})"
        ) from exc


def _points_entree(groupe: str) -> List[Any]:
    """Points d'entrée d'un groupe, quelle que soit la version de Python (3.9+).

    Depuis 3.10, `entry_points()` renvoie un objet *sélectionnable*
    (`.select(group=…)`) ; en 3.9, il renvoie un dictionnaire `{groupe: [...]}`.
    On détecte la première forme et retombe sur la seconde — plutôt que
    `entry_points(group=…)`, dont la signature n'existe pas en 3.9.
    """
    points = entry_points()
    selection = getattr(points, "select", None)
    if selection is not None:
        return list(selection(group=groupe))  # Python 3.10+
    return list(points.get(groupe, []))  # pragma: no cover - Python 3.9


class FabriqueGreffon(Fabrique):
    """Classe qui permet d'instancier les Greffons dont les Monteur ont été enregistrés.

    Il faut :

    1. enregistrer les monteurs des greffons avec `fabrique_greffons.charge_monteurs()`
       (liste explicite), ou `fabrique_greffons.decouvre_monteurs()` pour les
       découvrir automatiquement parmi les paquets installés (points d'entrée)
    2. instancier le type de greffon demandé, via `fabrique_greffons.active()`,
       qui lance `monteur.cree()` avec les arguments donnés, pour instancier le
       Greffon.

    NB : À défaut de Monteur, s'il n'y a pas de complexité pour instancier un
    Greffon (en particulier il n'y a pas plusieurs Greffons différents à
    instancier en fonction de la configuration utilisateur), alors on peut donner
    la classe du Greffon en tant que
    monteur et celle ci sera instanciée directement.
        Attention: pour que la classe Greffon se comporte comme un monteur, il faut
        qu'elle ait une propriété "clé".

    NB: Si on utilise un Monteur, on peut utiliser la même clé que le Greffon,
    tant qu'elle n'est pas utilisée par plusieurs Greffons ou Monteurs, puisqu'elle
    servira à
    déclencher l'instanciation du Monteur ou du Greffon associée.

    .. code-block:: python
        >>> from automatheque.greffon import fabrique_greffon
        >>> # dépend de l'argument donné à `charge_monteurs`
        >>> from plugin2.monteur import Monteur2
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
    ) -> Optional[Greffon]:
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
                    return None
                identifiant = instance_greffon.identifiant
            except Exception:
                LOGGER.exception(
                    f"Echec activation greffon : {identifiant} de type {cle_monteur}"
                )
                return None
        return Greffon.greffon_par_identifiant(identifiant)

    def charge_monteurs(
        self, liste_monteurs: List[Union[str, Type[Monteur], Type[Greffon]]]
    ) -> List[Monteur]:
        """Enregistre les monteurs de greffons disponibles dans la fabrique.

        Cela  pourrait etre fait de manière automatique, par ex en scannant un
        répertoire.
        Dans tous les cas ensuite il faut les activer un par un dans la configuration.
        """
        monteurs = []
        # `monteur` est résolu dynamiquement (via `_resout_reference`, importlib)
        # ou fourni par l'appelant : son type statique n'est pas connu.
        monteur: Any
        for elem in liste_monteurs:
            if isinstance(elem, str):
                monteur = _resout_reference(elem)
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

    def decouvre_monteurs(self, groupe: str = GROUPE_GREFFONS) -> List[Monteur]:
        """Découvre et enregistre les monteurs déclarés en *points d'entrée*.

        Un paquet tiers déclare ses greffons dans ses métadonnées, sans que
        l'application ait à les lister :

        .. code-block:: toml
            [project.entry-points."automatheque.greffons"]
            kodi = "monpaquet.kodi:MonteurKodi"

        C'est l'alternative « installe le paquet, c'est découvert » au
        `charge_monteurs([...])` explicite — et le remplacement propre du
        chargement d'une chaîne arbitraire par `pydoc.locate`.

        :param groupe: groupe de points d'entrée à scanner.
        :return: les monteurs enregistrés.
        """
        monteurs = [point.load() for point in _points_entree(groupe)]
        return self.charge_monteurs(monteurs)

    def active_greffons_conf(
        self,
        liste_greffons: Optional[List[str]] = None,
        configuration: Union[dict, ConfigParser, None] = None,
    ) -> List[Greffon]:
        """Active les greffons qui sont définis en conf dans l'option "greffons".

        Si liste_greffons est remplie, on ne charge que ces identifiants-ci et pas
        tous ceux définis en configuration.

        Si on utilise cette méthode pour activer les greffons, alors il est nécessaire
        de fournir un identifiant, on ne peut pas laisser automatheque créer
        l'identifiant
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
                liste_str = configuration["greffons"]["greffons"]
                liste_greffons = [i.strip() for i in liste_str.split(",")]
            except Exception as e:
                LOGGER.exception(e)
                raise ValueError(f"pas de liste de greffons dans {configuration}")

        greffons_actifs = []
        for identifiant in liste_greffons:
            conf = deepcopy(configuration[identifiant])
            cle = conf.pop("greffon")
            greffon = self.active(cle, identifiant=identifiant, **conf)
            # active() peut renvoyer None (greffon inactif ou échec) : on ne
            # l'ajoute pas — la méthode renvoie bien une List[Greffon].
            if greffon is not None:
                greffons_actifs.append(greffon)
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
