# -*- coding: utf-8 -*-
"""Réglages principaux de Automathèque."""

from os import environ, path


def _racine_config():
    """Racine de configuration de l'utilisateur, en honorant ``$XDG_CONFIG_HOME``.

    Renvoie ``$XDG_CONFIG_HOME`` s'il est défini et non vide, sinon ``~/.config``.
    """
    return environ.get("XDG_CONFIG_HOME") or path.join(path.expanduser("~"), ".config")


def repertoire_config():
    """Répertoire de configuration **partagé** d'automatheque.

    ``<racine>/automatheque/`` — réglages communs à tous les scripts (p. ex. SMTP).
    """
    return path.join(_racine_config(), "automatheque")


def repertoire_config_script(nom_court):
    """Répertoire de configuration **propre à un script** : ``<racine>/<nom_court>/``.

    C'est le foyer naturel du script : son ``config.ini`` et, par convention, son
    ``log.json``, ses données, son cache…
    """
    return path.join(_racine_config(), nom_court)

logger_config_dict = {
    "version": 1,
    # False : une bibliothèque ne doit pas désactiver les loggers déjà
    # configurés par l'application ou d'autres bibliothèques.
    "disable_existing_loggers": False,
    "formatters": {
        "automatheque": {"format": "%(asctime)s [%(levelname)s] %(name)s: %(message)s"}
    },
    "handlers": {
        "automatheque": {
            "level": "INFO",
            "formatter": "automatheque",
            "class": "logging.StreamHandler",
        }
    },
    "loggers": {
        "automatheque": {
            "handlers": ["automatheque"],
            "level": "DEBUG",
            "propagate": True,
        }
    },
}
