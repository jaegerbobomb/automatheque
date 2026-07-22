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

from automatheque import constantes


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


def test_dictconfig_depuis_ini_console_sur_la_racine():
    """`niveau` seul → handler console posé sur la **racine** (couvre tout).

    Régression #63 : la config d'un script doit viser la racine, pas seulement
    le logger `automatheque`.
    """
    config = ConfigParser()
    config.read_string("[log]\nniveau = warning\n")

    conf = _dictconfig_depuis_ini(config)

    assert conf["handlers"]["automatheque"]["class"] == "logging.StreamHandler"
    # Le handler n'a pas de niveau (NOTSET) : c'est la racine qui filtre.
    assert "level" not in conf["handlers"]["automatheque"]
    assert conf["root"]["handlers"] == ["automatheque"]
    assert conf["root"]["level"] == "WARNING"
    # Sans `names`, aucun logger nommé n'est surchargé.
    assert "loggers" not in conf


def test_dictconfig_depuis_ini_fichier_et_format():
    """`fichier` → FileHandler (sur la racine) ; `%%` dé-échappé en `%`."""
    config = ConfigParser()
    config.read_string(
        "[log]\nniveau = DEBUG\nfichier = /tmp/app.log\nformat = %%(message)s\n"
    )

    conf = _dictconfig_depuis_ini(config)

    handler = conf["handlers"]["automatheque"]
    assert handler["class"] == "logging.FileHandler"
    assert handler["filename"] == "/tmp/app.log"
    assert conf["root"]["handlers"] == ["automatheque"]
    assert conf["formatters"]["automatheque"]["format"] == "%(message)s"


def test_dictconfig_depuis_ini_names_niveaux_par_logger():
    """`names` fixe des niveaux par logger, sans handler propre (héritent root)."""
    config = ConfigParser()
    config.read_string(
        "[log]\n"
        "niveau = INFO\n"
        "names = automatheque:WARNING, mon_script:DEBUG, requests\n"
    )

    conf = _dictconfig_depuis_ini(config)

    loggers = conf["loggers"]
    assert loggers["automatheque"] == {"level": "WARNING", "propagate": True}
    assert loggers["mon_script"] == {"level": "DEBUG", "propagate": True}
    # Nom seul → niveau global.
    assert loggers["requests"] == {"level": "INFO", "propagate": True}
    # Aucun logger nommé ne porte de handler propre (pas de double-log).
    assert all("handlers" not in cfg for cfg in loggers.values())


def test_dictconfig_depuis_ini_names_seul_suffit():
    """`names` seul (sans niveau/format/fichier) déclenche quand même la config."""
    config = ConfigParser()
    config.read_string("[log]\nnames = mon_script:DEBUG\n")

    conf = _dictconfig_depuis_ini(config)

    assert conf is not None
    assert conf["loggers"]["mon_script"]["level"] == "DEBUG"


def test_dictconfig_depuis_ini_pourcent_non_echappe_message_clair():
    """Un `%` non échappé dans [log] lève une erreur claire invitant à doubler."""
    config = ConfigParser()
    config.read_string("[log]\nformat = %(asctime)s\n")

    with pytest.raises(ValueError, match="%%"):
        _dictconfig_depuis_ini(config)


def test_dictconfig_depuis_ini_pourcent_leve_configuration_invalide():
    """#26 : l'exception est `ConfigurationInvalide` (compatible ValueError)."""
    from automatheque.exceptions import (
        AutomathequeBaseException,
        ConfigurationInvalide,
    )

    config = ConfigParser()
    config.read_string("[log]\nformat = %(asctime)s\n")

    with pytest.raises(ConfigurationInvalide) as info:
        _dictconfig_depuis_ini(config)
    # Reste attrapable comme ValueError (rétro-compat) et via la hiérarchie maison.
    assert isinstance(info.value, ValueError)
    assert isinstance(info.value, AutomathequeBaseException)


def test_configure_logging_couvre_un_logger_quelconque():
    """#63 : `[log]` configure la racine → un logger de nom quelconque (le
    script via `getLogger(__name__)`, ses dépendances) reçoit le handler et le
    niveau, alors qu'avant seul `automatheque` était couvert."""
    config = ConfigParser()
    config.read_string("[log]\nniveau = DEBUG\n")

    _configure_logging(config)

    racine = logging.getLogger()
    assert racine.handlers  # la racine porte bien un handler
    quelconque = logging.getLogger("un_script_ou_une_dependance")
    assert quelconque.getEffectiveLevel() == logging.DEBUG


def test_configure_logging_names_surcharge_le_niveau_dun_logger():
    """#63 : `names = nom:NIVEAU` fixe le niveau d'un logger précis."""
    config = ConfigParser()
    config.read_string("[log]\nniveau = INFO\nnames = bavard:ERROR\n")

    _configure_logging(config)

    assert logging.getLogger("bavard").getEffectiveLevel() == logging.ERROR
    # Les autres restent au niveau global de la racine.
    assert logging.getLogger("autre").getEffectiveLevel() == logging.INFO


def test_racine_config_honore_xdg(monkeypatch, tmp_path):
    """`$XDG_CONFIG_HOME` est respecté quand il est défini."""
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    assert constantes._racine_config() == str(tmp_path)


def test_racine_config_defaut_sur_config(monkeypatch):
    """Sans `$XDG_CONFIG_HOME`, on retombe sur ~/.config."""
    monkeypatch.delenv("XDG_CONFIG_HOME", raising=False)
    assert constantes._racine_config().endswith("/.config")


def test_repertoire_config_par_script(monkeypatch, tmp_path):
    """Le répertoire par script est <racine>/<nom_court>/."""
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    assert constantes.repertoire_config_script("monscript") == str(
        tmp_path / "monscript"
    )


def test_charge_configuration_en_couches(monkeypatch, tmp_path):
    """La couche supplémentaire surcharge la couche partagée, qui sert de base."""
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))

    partage = tmp_path / "automatheque"
    partage.mkdir()
    (partage / "config.ini").write_text("[demo]\ncle = partagee\nbase = oui\n")

    (tmp_path / "monscript").mkdir()
    specifique = tmp_path / "monscript" / "config.ini"
    specifique.write_text("[demo]\ncle = specifique\n")

    cfg = charge_configuration([str(specifique)], ecraser=True, recharger=True)

    assert cfg.get("demo", "cle") == "specifique"  # la couche script surcharge
    assert cfg.get("demo", "base") == "oui"  # la couche partagée reste la base
