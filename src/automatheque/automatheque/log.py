# -*- coding: utf-8 -*-
"""Configure logging pour tout automatheque.

Contient quelques loggers par défaut pour les différents modules.
"""

import logging
import logging.config
import json

import yaml

from automatheque.constantes import logger_config_dict


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
                contenu = f.read()
            try:
                # Le fichier peut être au format JSON ou YAML : on tente JSON en
                # premier, et on retombe sur YAML s'il ne s'agit pas de JSON.
                conf = json.loads(contenu)
            except json.JSONDecodeError:
                conf = yaml.safe_load(contenu)
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


def configure_logging_defaut():
    """Active la configuration de logging par défaut d'automatheque.

    Pose un handler console sur le logger ``automatheque``. À appeler par une
    **application** (un script, p. ex. via ``@script_automatheque``), jamais à
    l'import d'une bibliothèque : configurer le logging global est le rôle de
    l'application, pas de la lib.
    """
    configure_logging(logger_config_dict)


def recup_logger(name="automatheque"):
    """Renvoie un logger (simple wrapper de ``logging.getLogger``).

    **Ne configure pas** le logging global : une bibliothèque ne doit pas le
    faire. C'est à l'application d'activer le logging quand elle le souhaite
    (``configure_logging`` / ``configure_logging_defaut``, ou
    ``@script_automatheque`` qui s'en charge pour les scripts).

    :param name: nom du logger demandé (passé à ``logging.getLogger``).
    """
    return logging.getLogger(name)


# Une bibliothèque ne configure pas le logging global à l'import : on se
# contente d'un NullHandler sur le logger « automatheque » (handler de dernier
# recours, évite « No handlers could be found »). L'application active le
# logging quand elle le veut, via configure_logging[_defaut].
logging.getLogger("automatheque").addHandler(logging.NullHandler())
