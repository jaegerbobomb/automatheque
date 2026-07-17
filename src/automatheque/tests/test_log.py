import json
import logging

from automatheque.log import (
    configure_logging,
    configure_logging_defaut,
)


def _config_logging_dict(nom_logger):
    """Renvoie une configuration dictConfig minimale et valide."""
    return {
        "version": 1,
        "disable_existing_loggers": False,
        "loggers": {nom_logger: {"level": "DEBUG"}},
    }


def test_configure_logging_charge_fichier_json(tmp_path):
    nom = "test_log_json"
    fichier = tmp_path / "log.json"
    fichier.write_text(json.dumps(_config_logging_dict(nom)))

    configure_logging(str(fichier))

    assert logging.getLogger(nom).level == logging.DEBUG


def test_import_pose_un_nullhandler_sur_le_logger_automatheque():
    """À l'import, la lib installe un NullHandler sur le logger `automatheque`.

    On recharge le module pour ré-exécuter sa logique d'import de façon
    déterministe : sinon un autre test de la suite peut avoir reconfiguré le
    logging global (dictConfig remplace les handlers), retirant le NullHandler.
    """
    import importlib

    from automatheque import log as _log

    importlib.reload(_log)

    handlers = logging.getLogger("automatheque").handlers
    assert any(isinstance(h, logging.NullHandler) for h in handlers)


def test_configure_logging_defaut_ne_desactive_pas_les_loggers_existants():
    """La config par défaut ne doit pas désactiver un logger préexistant
    (disable_existing_loggers = False)."""
    autre = logging.getLogger("un_logger_preexistant")
    autre.disabled = False

    configure_logging_defaut()

    assert autre.disabled is False


def test_configure_logging_charge_fichier_yaml(tmp_path):
    """Un fichier YAML doit être lu d'après son *contenu* (et non son chemin).

    Régression : auparavant ``yaml.safe_load`` recevait le chemin du fichier au
    lieu de son contenu, donc un fichier de log YAML n'était jamais chargé.
    """
    nom = "test_log_yaml"
    fichier = tmp_path / "log.yaml"
    fichier.write_text(
        "version: 1\n"
        "disable_existing_loggers: false\n"
        "loggers:\n"
        f"  {nom}:\n"
        "    level: DEBUG\n"
    )

    configure_logging(str(fichier))

    assert logging.getLogger(nom).level == logging.DEBUG
