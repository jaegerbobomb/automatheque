# -*- coding: utf-8 -*-
"""Chargement du fichier de configuration général."""

from os import path

from configparser import ConfigParser, NoOptionError, NoSectionError

from automatheque import constantes
from automatheque.log import recup_logger, configure_logging

fichier_config = "{}/config.ini".format(constantes.repertoire_config)

# Pour pouvoir tester relativement a une erreur automatheque:
NoOptionError = NoOptionError
NoSectionError = NoSectionError


def charge_configuration(fichiers_supplementaires=[], ecraser=False, recharger=False):
    """Fonction pour charger la configuration generale de automatheque."""
    if hasattr(charge_configuration, "config") and not recharger:
        return charge_configuration.config

    charge_configuration.config = ConfigParser()

    # On charge le logger ici, donc si la configuration a déjà été chargée on
    # est sûrs que recup_logger ne sera pas appelé de nouveau.
    # (ce que l'on souhaite vu que recup_logger appelle charge_configuration..)
    logger = recup_logger(__name__)

    # Pour écraser la configuration de automatheque on la charge en premier
    # et les fichiers suivants vont prendre la précédence.
    if ecraser:
        _charge_fichier_configuration(fichier_config, charge_configuration.config)

    # Ajout des autres fichiers s'il y en a :
    for f in fichiers_supplementaires:
        # Si "f" n'est pas un fichier, on regarde s'il existe dans le
        # répertoire de configuration d'automatheque.
        paths_a_tester = [f, path.join(constantes.repertoire_config, f)]
        for fichier in paths_a_tester:
            if not path.isfile(fichier):
                logger.debug("{} n'est pas un fichier.".format(fichier))
                continue

            _charge_fichier_configuration(fichier, charge_configuration.config)
            break  # TODO sauf si on veut charger les 2 fichiers ?
    # Si on veut conserver la configuration de automatheque, alors on charge
    # sa configuration en dernier :
    if not ecraser:
        _charge_fichier_configuration(fichier_config, charge_configuration.config)

    # Si la configuration que l'on vient d'importer contient des paramètres
    # qui concernent les logs alors on configure le logging :
    _configure_logging(charge_configuration.config)

    return charge_configuration.config


def _charge_fichier_configuration(fichier, config):
    recup_logger(__name__).debug(
        "Chargement du fichier de configuration : {}.".format(fichier)
    )
    config.read(fichier)


def _recup_fichier_config_log(config):
    """Renvoie le fichier de configuration des logs.

    S'il n'en trouve pas dans la configuration globale il renvoie log.json par
    défaut.
    """
    try:
        # TODO on ne doit pas forcer l'existence de la config 'log'
        fichier_config_log = config.get("log", "fichier_config", fallback="log.json")
    except NoOptionError:
        # TODO créer une exception custom
        msg = """Pas de configuration pour le fichier de log.
        Rappel structure:
        [log]
        fichier_config=chemin/vers/fichier/config.json ou .yaml"""
        recup_logger(__name__).exception(msg)
        raise
    return fichier_config_log


def _configure_logging(config):
    """Configure logging avec les valeurs définies dans le config.ini.

    Par défaut automatheque charge la configuration du fichier définit dans le
    config.ini dans la section :
    `[log]
    fichier_config=mon_fichierlog.json ou yaml
    `
    ou dans le fichier log.json à la racine du script s'il existe.

    Cette fonction est appelée automatiquement par charge_configuration à sa
    première exécution.

    :param desactive_loggers_existants: boolean Force ce paramètre de log
    """
    # Puis on ajoute la configuration trouvée dans le fichier de configuration
    # du logging, dont le chemin est stocké dans la configuration globale :

    try:
        fichier_config_log = _recup_fichier_config_log(config)
        desactive_loggers_existants = config.get(
            "log", "desactive_loggers_existants", fallback=None
        )
    except Exception:
        pass
    else:
        configure_logging(fichier_config_log, desactive_loggers_existants)
