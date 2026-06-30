import inspect
import json
import logging
from configparser import ConfigParser, NoSectionError
from unittest.mock import MagicMock

import pytest
from automatheque.configuration import (
    _configure_logging,
    _dictconfig_depuis_ini,
    charge_configuration,
)


def test_charge_configuration_defaut_non_mutable():
    """L'argument par défaut ne doit pas être une liste mutable partagée."""
    defaut = (
        inspect.signature(charge_configuration)
        .parameters["fichiers_supplementaires"]
        .default
    )
    assert defaut is None


def test_configure_logging_section_log_absente_ne_leve_pas():
    """Si la lecture de la config de log échoue (section/option absente),
    _configure_logging journalise et n'interrompt pas le chargement."""
    config = MagicMock()
    config.get.side_effect = NoSectionError("log")

    # Ne doit pas lever :
    _configure_logging(config)


def test_configure_logging_erreur_inattendue_se_propage():
    """Une erreur sans rapport avec la config (ex: ValueError) n'est plus
    avalée silencieusement par un except trop large : elle remonte."""
    config = MagicMock()
    config.get.side_effect = ValueError("erreur inattendue")

    with pytest.raises(ValueError):
        _configure_logging(config)


def test_configure_logging_sans_section_log_ne_fait_rien():
    """Pas de section [log] : aucun effet, et surtout aucune exception."""
    _configure_logging(ConfigParser())


def test_configure_logging_fichier_config_prioritaire(tmp_path):
    """`fichier_config` charge un dictConfig externe (ici JSON)."""
    fichier = tmp_path / "log.json"
    fichier.write_text(
        json.dumps(
            {
                "version": 1,
                "disable_existing_loggers": False,
                "loggers": {"un_test_fichier_config": {"level": "DEBUG"}},
            }
        )
    )
    config = ConfigParser()
    config.read_string("[log]\nfichier_config = {}\n".format(fichier))

    _configure_logging(config)

    assert logging.getLogger("un_test_fichier_config").level == logging.DEBUG


def test_dictconfig_depuis_ini_none_sans_cles():
    """Section [log] sans clé simple → rien à fabriquer."""
    config = ConfigParser()
    config.add_section("log")
    assert _dictconfig_depuis_ini(config) is None


def test_dictconfig_depuis_ini_console_par_defaut():
    """`niveau` seul → handler console, niveau normalisé en majuscules."""
    config = ConfigParser()
    config.read_string("[log]\nniveau = warning\n")

    conf = _dictconfig_depuis_ini(config)

    assert conf["handlers"]["automatheque"]["class"] == "logging.StreamHandler"
    assert conf["loggers"]["automatheque"]["level"] == "WARNING"


def test_dictconfig_depuis_ini_fichier_et_format():
    """`fichier` → FileHandler ; `format` avec `%%` est dé-échappé en `%`."""
    config = ConfigParser()
    config.read_string(
        "[log]\nniveau = DEBUG\nfichier = /tmp/app.log\nformat = %%(message)s\n"
    )

    conf = _dictconfig_depuis_ini(config)

    handler = conf["handlers"]["automatheque"]
    assert handler["class"] == "logging.FileHandler"
    assert handler["filename"] == "/tmp/app.log"
    assert conf["formatters"]["automatheque"]["format"] == "%(message)s"


def test_dictconfig_depuis_ini_pourcent_non_echappe_message_clair():
    """Un `%` non échappé dans [log] lève un ValueError qui invite à doubler."""
    config = ConfigParser()
    config.read_string("[log]\nformat = %(asctime)s\n")

    with pytest.raises(ValueError, match="%%"):
        _dictconfig_depuis_ini(config)
