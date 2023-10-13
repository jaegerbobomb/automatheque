# -*- coding: utf-8 -*-
"""Réglages principaux de Automathèque."""

from os import path

# Répertoire où stocker les principaux réglages de Automathèque.
repertoire_config = "{}/.config/automatheque".format(path.expanduser("~"))

logger_config_dict = {
    "version": 1,
    "disable_existing_loggers": True,
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
