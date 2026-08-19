# -*- coding: utf-8 -*-
"""Chargement du fichier de configuration général."""

import logging
from configparser import (
    ConfigParser,
    InterpolationError,
    NoOptionError,
    NoSectionError,
)
from os import path

import attr

from automatheque import constantes
from automatheque.exceptions import ConfigurationInvalide
from automatheque.log import configure_logging


def fichier_config():
    """Chemin du ``config.ini`` **partagé** d'automatheque (couche de base)."""
    return path.join(constantes.repertoire_config(), "config.ini")


def charge_configuration(fichiers_supplementaires=None, ecraser=False, recharger=False):
    """Fonction pour charger la configuration generale de automatheque."""
    if hasattr(charge_configuration, "config") and not recharger:
        return charge_configuration.config

    if fichiers_supplementaires is None:
        fichiers_supplementaires = []

    charge_configuration.config = ConfigParser()

    logger = logging.getLogger(__name__)

    # Pour écraser la configuration de automatheque on la charge en premier
    # et les fichiers suivants vont prendre la précédence.
    if ecraser:
        _charge_fichier_configuration(fichier_config(), charge_configuration.config)

    # Ajout des autres fichiers s'il y en a :
    for f in fichiers_supplementaires:
        # Si "f" n'est pas un fichier, on regarde s'il existe dans le
        # répertoire de configuration partagé d'automatheque.
        paths_a_tester = [f, path.join(constantes.repertoire_config(), f)]
        for fichier in paths_a_tester:
            if not path.isfile(fichier):
                logger.debug("{} n'est pas un fichier.".format(fichier))
                continue

            _charge_fichier_configuration(fichier, charge_configuration.config)
            # On s'arrête au PREMIER emplacement trouvé : `paths_a_tester` est un
            # mécanisme de *résolution* (« où se trouve `f` ? »), pas de fusion.
            # Les deux chemins désignent le même nom de fichier à deux endroits ;
            # les charger tous les deux fusionnerait deux fichiers homonymes sans
            # lien voulu. Pour superposer plusieurs configurations, passer
            # plusieurs entrées dans `fichiers_supplementaires` (traitées dans
            # l'ordre, chacune surchargeant la précédente). Cf. #27.
            break
    # Si on veut conserver la configuration de automatheque, alors on charge
    # sa configuration en dernier :
    if not ecraser:
        _charge_fichier_configuration(fichier_config(), charge_configuration.config)

    # Si la configuration que l'on vient d'importer contient des paramètres
    # qui concernent les logs alors on configure le logging :
    _configure_logging(charge_configuration.config)

    return charge_configuration.config


def _charge_fichier_configuration(fichier, config):
    logging.getLogger(__name__).debug(
        "Chargement du fichier de configuration : {}.".format(fichier)
    )
    config.read(fichier)


def _configure_logging(config):
    """Configure le logging d'après la section ``[log]`` de la configuration.

    Précédence (plus aucune découverte magique de fichier au ``cwd``) :

    1. ``fichier_config`` → chemin d'un dictConfig externe (JSON **ou** YAML,
       détecté d'après son contenu) ;
    2. sinon, clés simples ``niveau`` / ``fichier`` / ``format`` dans ``[log]``
       → un dictConfig minimal est fabriqué à la volée ;
    3. sinon, rien (le logging par défaut éventuellement posé par l'application
       — cf. ``log.configure_logging_defaut`` — reste en place).

    Appelée automatiquement par ``charge_configuration``. N'interrompt jamais le
    chargement de la configuration si la section/option est absente.
    """
    try:
        if not config.has_section("log"):
            logging.getLogger(__name__).debug(
                "Section [log] absente : logging inchangé."
            )
            return
        fichier_config_log = config.get("log", "fichier_config", fallback=None)
        desactive_loggers_existants = config.get(
            "log", "desactive_loggers_existants", fallback=None
        )
    except (NoOptionError, NoSectionError):
        logging.getLogger(__name__).debug(
            "Pas de configuration de logging exploitable dans [log]."
        )
        return

    if fichier_config_log:
        configure_logging(fichier_config_log, desactive_loggers_existants)
        return

    conf = _dictconfig_depuis_ini(config)
    if conf is not None:
        if desactive_loggers_existants is not None:
            conf["disable_existing_loggers"] = desactive_loggers_existants
        configure_logging(conf)


def _dictconfig_depuis_ini(config):
    """Construit un dictConfig minimal depuis des clés simples de ``[log]``.

    Un script étant une **application**, cette forme configure la **racine**
    (root) : le logger propre du script (``getLogger(__name__)``) comme ceux des
    dépendances héritent tous du handler. Cf. #63.

    Clés reconnues (toutes optionnelles) :

    * ``niveau``  : niveau global (celui de la racine ; défaut ``INFO``) ;
    * ``fichier`` : si présent, journalise dans ce fichier (sinon console) ;
    * ``format``  : format des messages. Les ``%`` doivent être **échappés en
      ``%%``** (convention ConfigParser, comme partout ailleurs dans le ``.ini``),
      p. ex. ``format = %%(asctime)s [%%(levelname)s] %%(name)s: %%(message)s`` ;
    * ``names``   : **niveaux par logger**, séparés par des virgules. Chaque
      entrée est ``nom`` (→ niveau global) ou ``nom:NIVEAU``. Exemple :
      ``names = automatheque:WARNING, mon_script:DEBUG, requests:ERROR``. Le
      handler/destination reste **partagé** (un seul) ; pour router des loggers
      vers des fichiers distincts, utiliser ``fichier_config`` (dictConfig
      complet en JSON/YAML).

    Renvoie ``None`` si aucune de ces clés n'est présente (rien à configurer).

    :raise ConfigurationInvalide: si une valeur contient un ``%`` non échappé
        (message explicite invitant à doubler le ``%``). Cette exception hérite
        aussi de ``ValueError`` (rétro-compat des appelants existants).
    """
    cles = ("niveau", "fichier", "format", "names")
    if not any(config.has_option("log", c) for c in cles):
        return None

    try:
        niveau = config.get("log", "niveau", fallback="INFO").upper()
        fmt = config.get(
            "log",
            "format",
            fallback="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        )
        fichier = config.get("log", "fichier", fallback=None)
        names_brut = config.get("log", "names", fallback="")
    except InterpolationError as exc:
        raise ConfigurationInvalide(
            "Section [log] : un '%' non échappé. Doublez-le en '%%' (convention "
            "ConfigParser), p. ex. format = %%(asctime)s %%(message)s. [{}]".format(exc)
        ) from exc

    if fichier:
        handler = {
            "class": "logging.FileHandler",
            "filename": fichier,
            "formatter": "automatheque",
        }
    else:
        handler = {
            "class": "logging.StreamHandler",
            "formatter": "automatheque",
        }

    conf = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {"automatheque": {"format": fmt}},
        # Le handler n'a pas de niveau (NOTSET) : ce sont les niveaux des loggers
        # (racine + surcharges `names`) qui filtrent.
        "handlers": {"automatheque": handler},
        "root": {"handlers": ["automatheque"], "level": niveau},
    }

    loggers = {}
    for entree in names_brut.split(","):
        entree = entree.strip()
        if not entree:
            continue
        nom, sep, niv = entree.partition(":")
        nom = nom.strip()
        niv = niv.strip().upper() if sep else niveau
        # Pas de handler propre : le logger hérite du handler de la racine (un
        # seul affichage, pas de double-log) ; on n'ajuste que son niveau.
        loggers[nom] = {"level": niv, "propagate": True}
    if loggers:
        conf["loggers"] = loggers

    return conf


# --- Validation d'une section de configuration (#12) ------------------------
#
# `charge_configuration` renvoie un `ConfigParser` brut : tout est chaîne, rien
# n'est validé, et une clé manquante ou mal typée n'explose que tard, au point
# d'accès, loin de sa cause. On décrit ici une section comme une classe attrs
# typée et validée, peuplée en un appel — la validation a lieu une fois, tôt,
# avec une erreur qui nomme la section et la clé.

_BOOLEENS_VRAI = frozenset({"1", "yes", "true", "on", "oui", "vrai"})
_BOOLEENS_FAUX = frozenset({"0", "no", "false", "off", "non", "faux"})


def booleen(valeur):
    """Converteur ``.ini`` → ``bool`` pour un champ attrs.

    Un ``ConfigParser`` ne rend que des chaînes ; ce converteur reconnaît les
    graphies usuelles (``yes``/``no``, ``true``/``false``, ``on``/``off``,
    ``1``/``0``, et ``oui``/``non``, ``vrai``/``faux``), casse et espaces
    indifférents. Un booléen déjà typé passe tel quel (utile pour instancier la
    classe hors configuration).

    .. code-block:: python

        actif = attr.ib(default=False, converter=booleen)

    :raise ValueError: si la valeur n'est pas une graphie booléenne reconnue.
        Levée à la construction, `charge_section` la retraduit en
        `ConfigurationInvalide` contextualisée.
    """
    if isinstance(valeur, bool):
        return valeur
    if isinstance(valeur, str):
        v = valeur.strip().lower()
        if v in _BOOLEENS_VRAI:
            return True
        if v in _BOOLEENS_FAUX:
            return False
    raise ValueError("valeur booléenne non reconnue : {!r}".format(valeur))


def liste(valeur, separateur=","):
    """Converteur ``.ini`` → ``list[str]`` (valeurs séparées par des virgules).

    Chaque élément est détouré ; les éléments vides sont ignorés (``"a, ,b"`` →
    ``["a", "b"]``). Une liste/un tuple déjà typé passe tel quel. Rend explicite
    le motif ``valeur.split(",")`` éparpillé dans le code de configuration.

    .. code-block:: python

        greffons = attr.ib(factory=list, converter=liste)

    :raise ValueError: si la valeur n'est ni une chaîne, ni une séquence.
    """
    if isinstance(valeur, (list, tuple)):
        return list(valeur)
    if isinstance(valeur, str):
        return [
            element.strip() for element in valeur.split(separateur) if element.strip()
        ]
    raise ValueError("valeur de liste non reconnue : {!r}".format(valeur))


def charge_section(cls, config, section, strict=True):
    """Peuple et valide une classe attrs depuis une section de configuration.

    Chaque option de ``[section]`` est passée à ``cls`` en argument nommé ; les
    ``converter``/``validator`` des ``attr.ib`` font la conversion (chaîne →
    ``int``, :func:`booleen`, :func:`liste`…) et le contrôle. Le résultat est
    une instance **peuplée et validée**, ou une erreur **précoce** qui nomme la
    section et la clé fautive.

    .. code-block:: python

        @attr.s
        class ConfigSmtp:
            hote = attr.ib(validator=attr.validators.instance_of(str))
            port = attr.ib(default=465, converter=int)

        smtp = charge_section(ConfigSmtp, charge_configuration(), "smtp")

    Les noms d'options du ``.ini`` sont — convention ``ConfigParser`` — en
    minuscules ; ils doivent correspondre aux champs de ``cls``.

    :param cls: classe décorée ``attrs`` (``@attr.s`` / ``@define``).
    :param config: le ``ConfigParser`` (ce que renvoie `charge_configuration`).
    :param section: nom de la section ``[section]``.
    :param strict: si ``True`` (défaut), une option **inconnue** de ``cls`` est
        une erreur (elle rattrape les fautes de frappe) ; si ``False``, les
        options inconnues sont ignorées (utile quand la section sert aussi à
        d'autres consommateurs).
    :raise ConfigurationInvalide: section absente, option inconnue (en mode
        strict), champ requis manquant, ou valeur refusée par un
        converter/validator. Hérite de ``ValueError``.
    :raise TypeError: si ``cls`` n'est pas une classe attrs.
    """
    if not attr.has(cls):
        raise TypeError(
            "charge_section attend une classe attrs, pas {!r}".format(
                getattr(cls, "__name__", cls)
            )
        )
    if not config.has_section(section):
        raise ConfigurationInvalide(
            "section [{}] absente de la configuration".format(section)
        )

    options = dict(config.items(section))

    # Nom d'initialisation de chaque champ (attrs retire les underscores de tête
    # pour l'argument du constructeur ; `alias` le fixe explicitement au besoin).
    champs = {}
    requis = []
    for champ in attr.fields(cls):
        nom_init = getattr(champ, "alias", None) or champ.name.lstrip("_")
        champs[nom_init] = champ
        if champ.default is attr.NOTHING:
            requis.append(nom_init)

    if strict:
        inconnues = sorted(set(options) - set(champs))
        if inconnues:
            raise ConfigurationInvalide(
                "section [{}] : option(s) inconnue(s) : {} (attendu : {})".format(
                    section, ", ".join(inconnues), ", ".join(sorted(champs))
                )
            )
    else:
        options = {nom: val for nom, val in options.items() if nom in champs}

    manquantes = sorted(nom for nom in requis if nom not in options)
    if manquantes:
        raise ConfigurationInvalide(
            "section [{}] : clé(s) requise(s) manquante(s) : {}".format(
                section, ", ".join(manquantes)
            )
        )

    try:
        return cls(**options)
    except (TypeError, ValueError) as exc:
        # Un converter/validator a rejeté une valeur (`instance_of` lève un
        # TypeError, `int("x")` un ValueError) : on la retraduit en erreur de
        # configuration contextualisée plutôt que de laisser fuiter l'erreur brute.
        raise ConfigurationInvalide(
            "section [{}] : valeur invalide ({})".format(section, exc)
        ) from exc
