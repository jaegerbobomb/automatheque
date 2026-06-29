# -*- coding: utf-8 -*-
"""Tests du harness de test des scripts (essai.py)."""

from automatheque.essai import (
    ResultatScript,
    ecris_config,
    execute_script,
    reinitialise_configuration,
)
from automatheque.util.script import ScriptAutomatheque

DOC = """Script de démonstration.

Usage:
  prog [--action] [--config=<fichier>]

Options:
  --action            Réalise l'action.
  --config=<fichier>  Fichier de configuration.
"""


def test_execute_script_parse_argv_et_renvoie_le_resultat():
    """L'argv contrôlé est parsé et la valeur de retour est remontée."""

    def main(_script=None):
        return _script.arguments["--action"]

    res = execute_script(DOC, main, argv=["--action"])

    assert isinstance(res, ResultatScript)
    assert res.resultat is True
    assert isinstance(res.script, ScriptAutomatheque)
    assert res.script.arguments["--action"] is True


def test_execute_script_sans_argument():
    """Sans `--action`, l'argument est faux."""
    res = execute_script(DOC, lambda _script=None: _script.arguments["--action"])
    assert res.resultat is False


def test_execute_script_charge_la_config_via_option_config(tmp_path):
    """Un `--config` pointant un .ini jetable peuple `script.config`."""
    fichier = ecris_config(tmp_path / "conf.ini", "[demo]\ncle = valeur\n")

    res = execute_script(DOC, lambda _script=None: None, argv=["--config", fichier])

    assert res.script.config.get("demo", "cle") == "valeur"


def test_reinitialise_configuration_efface_le_cache():
    """`reinitialise_configuration` oublie le singleton de configuration."""
    from automatheque.configuration import charge_configuration

    charge_configuration(ecraser=True, recharger=True)
    assert hasattr(charge_configuration, "config")

    reinitialise_configuration()
    assert not hasattr(charge_configuration, "config")
