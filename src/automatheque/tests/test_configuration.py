import inspect
from configparser import NoSectionError
from unittest.mock import MagicMock

import pytest
from automatheque.configuration import _configure_logging, charge_configuration


def test_charge_configuration_defaut_non_mutable():
    """L'argument par défaut ne doit pas être une liste mutable partagée."""
    defaut = inspect.signature(charge_configuration).parameters[
        "fichiers_supplementaires"
    ].default
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

