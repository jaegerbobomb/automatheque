# -*- coding=utf-8 -*-
"""Permet d'importer tous les plugins configurés, et de lister leur capacités.

Pour les plugins internes il suffit de faire un PluginAutomatheque + Singleton, il n'y
a pas besoin de faire des Monteurs pour ça. 
(par exemple voir plugins.decomposition.decomposeurs_film.py)
TODO pas sûr que cet exemple marche bien
les plugins decomposeurs sont pas utilisés par capacité
et on peut charger un plugin sans monteur juste en mettant la classe ...

TODO : judicieux de prendre le nom du fichier comme clé par défaut pour monteur + plugin ?
"""
from copy import deepcopy
import uuid

import attr
from automatheque.conception.structures import Fabrique, MetaInstanceRegistre
from automatheque.configuration import charge_configuration, ConfigParser
from automatheque.log import recup_logger
from automatheque.util.classe import classproperty


LISTE_PLUGINS_DEFAUT = [
    "automatheque.plugins.kodi.MonteurKodi",
    "automatheque.plugins.trakt.MonteurTrakt",
]

# TODO il faut faire une interface par "capacite"
DECOMPOSITION = "decomposition"
EPISODE_INFOS = "episode_infos"
EPISODE_EST_VISIONNE = "episode_est_visionne"
FILM_EST_VISIONNE = "film_est_visionne"
FILM_INFOS = "film_infos"

__all__ = [
    "DECOMPOSITION",
    "EPISODE_EST_VISIONNE",
    "EPISODE_INFOS",
    "FILM_EST_VISIONNE",
    "FILM_INFOS",
    "PluginAutomatheque",
]

LOGGER = recup_logger(__name__)
LOGGER.debug("LOGGER")


class RegistrePlugins(metaclass=MetaInstanceRegistre):
    @classmethod
    def plugins_charge_defaut(cls, fabrique_plugin, force=False):
        fabrique_plugin.plugins_charge_defaut()
        plugins_actives = fabrique_plugin.active_plugins_conf()
        LOGGER.debug(f"Plugins activés : {plugins_actives}")
        return plugins_actives

    @classmethod
    def plugins_par_capacite(cls, capacite):
        if not cls._recup_instances(recursive=True):
            cls.plugins_charge_defaut(fabrique_plugin=fabrique_plugin)
        return [
            p for p in cls._recup_instances(recursive=True) if capacite in p.capacites
        ]

    @classmethod
    def plugins_identifiants(cls):
        return [p.identifiant for p in cls._recup_instances(recursive=True)]

    @classmethod
    def plugin_par_identifiant(
        cls, identifiant
    ) -> Union[PluginAutomatheque, None]:  # typing preload
        plugins = [
            p
            for p in cls._recup_instances(recursive=True)
            if p.identifiant == identifiant
        ]
        return plugins[0] if plugins else None


@attr.s(eq=False)  # pour rendre la classe hashable pour le weakrefset du registre
class PluginAutomatheque(RegistrePlugins):
    # TODO il manque self.capacites !
    # comment le remplir en remontant les héritages ?
    # ex si plugin(PluginAutomatheque, CapaciteEpisodeInfos)
    # ou alors self.capacites = [ CapaciteEpisodeInfos(self), Capacite... ]
    # et dans les capacites : self.recup_infos = plugin.recup_infos
    # => il parait que c'est mieux mais c'est pas ultra clair ...
    # homeassistant ("manifest") vs weboob quoi

    # De plus où ranger les capacites ? automatheque/plugins/capacites/1.py , 2
    # ou automatheque/plugin/capacites + automatheque/plugins/plugin1.py etc. ?
    # ou automatheque... + automatheque/plugin/plugins/plugin1 ...

    # Utilisation de kw_only=True pour l'héritage :
    # https://github.com/python-attrs/attrs/issues/38
    # Il faut utiliser l'option également dans les classes filles.
    identifiant = attr.ib(default=str(uuid.uuid4()), kw_only=True)
    config_requise = attr.ib(default=False, init=False, kw_only=True)
    config = attr.ib(init=False, factory=charge_configuration, kw_only=True)

    @classproperty
    def cle(cls):
        """Retourne le nom de la classe sans "Plugin" en minuscule"""
        return (
            cls.__name__[0:-6].lower()
            if cls.__name__.lower().startswith("plugin")
            else cls.__name__.lower()
        )  # ?

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
        LOGGER.debug("Plugin : {} - debut appel".format(self.cle))


class FabriquePlugin(Fabrique):
    """Classe qui permet d'instancier les Plugins dont les Monteur ont été enregistrés.

    Il faut dans un premier temps enregistrer les monteurs des plugins par la fonction
    enregistre_plugins, puis il faut activer le plugin donné ce qui lance
    monteur.cree avec les arguments donnés.
    """

    def active(self, cle_monteur, identifiant, *args, **kwargs):
        """Va chercher dans le registre des plugins et renvoie le plugin activé.

        S'il ne trouve pas le plugin il en instancie un autre.
        TODO : comme identifiant peut etre auto génré on devrait pouvoir
        le rendre facultatif si on ne veut pas l'appeler nommément ? ou mettre clé ?
        """
        if identifiant not in PluginAutomatheque.plugins_identifiants():
            # plugins.keys():
            try:
                instance_plugin = self.cree(
                    cle_monteur, *args, identifiant=identifiant, **kwargs
                )
                LOGGER.debug(f"Plugin activé : {instance_plugin}")
                if not instance_plugin.actif:
                    LOGGER.warning(f"Plugin {instance_plugin} inactif")
                    return False
            except Exception:
                LOGGER.exception(f"Echec activation plugin : {identifiant}")
        return PluginAutomatheque.plugin_par_identifiant(identifiant)

    def enregistre_plugins(self, liste_plugins):
        """Enregistre les plugins disponibles dans la fabrique.

        Cela  pourrait etre fait de manière automatique, par ex en scannant un
        répertoire.
        Dans tous les cas ensuite il faut les activer un par un dans la configuration.
        """
        monteurs = []
        for elem in liste_plugins:
            from pydoc import locate

            monteur = locate(elem)  # ou importlib TODO ?
            if sans_monteur:
                # Pas de monteur, on reçoit la classe directement, donc on ne l'instancie pas nous même
                # TODO : si monteur est un pluginautomatheqe alors il y a déjà "cle"
                monteurs.append(
                    self.enregistre_monteur(monteur.cle or elem.split(".")[-2], monteur)
                )
            else:
                monteurs.append(
                    self.enregistre_monteur(
                        # TODO utilisation du nom du fichier comme clé par défaut...
                        monteur.cle or elem.split(".")[-2],
                        monteur(),
                    )
                )
        return monteurs

    def plugins_charge_defaut(self):
        """Charge les plugins par défaut dans la liste de monteurs."""
        self.enregistre_plugins(LISTE_PLUGINS_DEFAUT)
        LOGGER.debug(f"Plugins chargés : {self.recup_monteurs()}")

    def active_plugins_conf(self, liste_plugins=None, configuration=None):
        """Active les plugins qui sont définis en conf dans l'option "plugins".

        .. example ::
            [plugins]
            plugins=kodi1,trakt1

            [kodi1]
            plugin=kodi
            hote=xxx
            [trakt1]
            plugin=trakt

        configuration peut aussi être un dictionnaire équivalent.
        """
        if configuration is None:
            configuration = dict(charge_configuration())
        elif isinstance(configuration, ConfigParser):
            configuration = dict(configuration)
        elif not isinstance(configuration, dict):
            raise ValueError(f"configuration n'est pas au bon format")

        if liste_plugins is None:
            try:
                # On laisse dans "plugin" si on veut sortir le code un jour !
                liste_plugins = configuration.get("plugins").get("plugins")
                liste_plugins = [i.strip() for i in liste_plugins.split(",")]
            except Exception as e:
                raise ValueError(f"pas de liste de plugins dans {configuration}")

        plugins_actives = []
        for identifiant in liste_plugins:
            conf = deepcopy(configuration.get(identifiant))
            cle = conf.pop("plugin")
            plugins_actives.append(self.active(cle, identifiant, **conf))
        return plugins_actives


fabrique_plugin = FabriquePlugin()
