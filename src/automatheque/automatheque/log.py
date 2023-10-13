# -*- coding: utf-8 -*-
"""Configure logging pour tout automatheque.

Contient quelques loggers par défaut pour les différents modules.
"""

import logging
import logging.config
import json

import yaml

from automatheque.constantes import logger_config_dict

# Python2 n'a pas "FileNotFoundError"
try:
    FileNotFoundError
except NameError:
    FileNotFoundError = IOError


def configure_logging(conf, desactive_loggers_existants=None):
    """Configure le logging à partir de la conf donnée en paramètre."""
    # TODO https://github.com/yaml/pyyaml/issues/116
    # Tant que pyyaml ne gèrera pas yaml1.2 il faudra faire le test pour savoir
    # si la conf est en json ou en yaml. Ensuite on pourra charger le fichier
    # sans se poser de questions.
    try:
        # logging.config.fileConfig est remplacé par dictConfig, donc on stocke
        # la configuration sous forme de json dans le fichier au lieu du format
        # demandé par fileConfig (ou directement sous forme de dictionnaire).
        if isinstance(conf, str):
            with open(conf, "r") as f:
                try:
                    conf = json.load(f)
                except:
                    pass
                try:
                    conf = yaml.safe_load(conf)
                except:
                    pass
        elif not isinstance(conf, dict):
            raise ValueError("conf doit etre un fichier ou un dictionnaire")
    except FileNotFoundError:
        # configure_logging a déjà été joué au moins une fois avec la config
        # présente dans les constantes, donc recup_logger renvoie bien qqch.
        recup_logger(__name__).warning("Fichier absent : {}".format(conf))
    else:
        if desactive_loggers_existants is not None:
            # on peut forcer True ou False
            conf["disable_existing_loggers"] = desactive_loggers_existants
        logging.config.dictConfig(conf)


def logger_existe(nom):
    """Renvoie True si le logger a déjà été déclaré. False sinon."""
    existe = True
    if nom not in logging.Logger.manager.loggerDict:
        existe = False
    return existe


def recup_logger(name="automatheque"):
    """Renvoie un logger : wrapper autour de logging.

    Charge la configuration de l'application et celle du logging si cela n'a
    pas encore été fait, puis renvoie le logger demandé.
    Renvoie le logger "automatheque" par défaut, défini dans les constantes.

    Par défaut automatheque charge la configuration du fichier définit dans le
    config.ini, dans la section :
    .. code-block:: ini
        [log]
        fichier_config=mon_fichierlog.json

    ou dans le fichier log.json à la racine du script appelant s'il existe.

    :param name:  Nom du logger demandé (passé à logging.getLogger())
    """
    # charge_configuration() utilise aussi recup_logger mais il ne l'appelle
    # que si la configuration n'a pas encore été chargée.
    from automatheque.configuration import charge_configuration

    # Si la configuration a déjà été chargée alors logging est déjà paramétré
    # et charge_configuration() ne fait rien.
    charge_configuration()
    # TODO pour gagner en perf on peut aussi garder un attribut "deja_joue" par
    # exemple pour éviter d'appeler charge_configuration à chaque fois.

    lg = logging.getLogger(name)
    return lg


# D'abord on configure le logging par défaut d'automatheque
configure_logging(logger_config_dict)
