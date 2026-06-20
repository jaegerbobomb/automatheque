import json
import logging

from automatheque.log import configure_logging


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
