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

from automatheque import constantes
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
            break  # TODO(#27) sauf si on veut charger les 2 fichiers ?
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

    :raise ValueError: si une valeur contient un ``%`` non échappé (message
        explicite invitant à doubler le ``%``).
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
        raise ValueError(
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
