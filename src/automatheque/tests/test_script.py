"""Tests de la promotion de l'API script (#41).

`script_automatheque` / `script` / `ScriptAutomatheque` vivent désormais dans
`automatheque.script`. `automatheque.util.script` reste un shim de
rétrocompatibilité qui ré-exporte les mêmes objets et émet un
`DeprecationWarning` à l'import.
"""

import importlib
import logging
import sys
import warnings

import attr
import commandopt
import pytest
from automatheque.essai import execute_script, reinitialise_configuration
from automatheque.script import (
    OPTIONS_INTERNES,
    ScriptAutomatheque,
    commande,
    script_automatheque,
)
from commandopt import NoCommandFoundError, Registry

#: Usage docopt déclarant les commodités câblées par #5.
DOC_OPTIONS = """Script de démonstration des options.

Usage:
  demo [--dry-run] [-v | -q]

Options:
  --dry-run     N'effectue aucune action définitive.
  -v --verbose  Journalisation DEBUG.
  -q --quiet    Journalisation WARNING.
"""


def _noop(_script=None):
    return "ok"


def test_import_depuis_le_nouvel_emplacement():
    """Le nouvel emplacement expose bien l'API et son alias court."""
    from automatheque.script import (
        ScriptAutomatheque,
        script,
        script_automatheque,
    )

    assert script is script_automatheque
    assert callable(script_automatheque)
    assert isinstance(ScriptAutomatheque, type)


def test_shim_util_script_emet_un_deprecationwarning():
    """L'ancien chemin reste importable mais prévient de la dépréciation.

    On recharge le module pour que l'avertissement soit ré-émis même si un
    autre test (ou import) l'a déjà chargé auparavant.
    """
    import automatheque.util.script as ancien

    with warnings.catch_warnings(record=True) as captures:
        warnings.simplefilter("always")
        importlib.reload(ancien)

    assert any(
        issubclass(c.category, DeprecationWarning)
        and "automatheque.script" in str(c.message)
        for c in captures
    )


def test_shim_reexporte_les_memes_objets():
    """Le shim pointe vers les objets canoniques, pas des copies."""
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", DeprecationWarning)
        import automatheque.script as nouveau
        import automatheque.util.script as ancien

    assert ancien.script_automatheque is nouveau.script_automatheque
    assert ancien.ScriptAutomatheque is nouveau.ScriptAutomatheque
    assert ancien.script is nouveau.script


# --- #24 : ScriptAutomatheque en attrs + pilotage hors sys.argv ----------------


def test_script_est_une_classe_attrs():
    """#24 : ScriptAutomatheque est désormais une classe attrs."""
    assert attr.has(ScriptAutomatheque)


def test_nom_court_derive_du_nom():
    """`nom_court` est dérivé de `nom` (basename sans `.py`)."""
    s = ScriptAutomatheque(nom="/chemin/mon_script.py", chaine_docopt="doc")
    assert s.nom_court == "mon_script"


def test_repr_ne_deverse_pas_la_chaine_docopt():
    """Le repr attrs masque la chaîne docopt (verbeuse) et le logger."""
    s = ScriptAutomatheque(nom="x.py", chaine_docopt="USAGE ENORME " * 50)
    rendu = repr(s)
    assert "chaine_docopt" not in rendu
    assert "ENORME" not in rendu
    assert "x.py" in rendu  # les champs utiles restent visibles


def test_script_reste_hachable_et_par_identite():
    """`eq=False` : identité préservée (hachable, pas d'égalité par valeur)."""
    a = ScriptAutomatheque(nom="x.py", chaine_docopt="doc")
    b = ScriptAutomatheque(nom="x.py", chaine_docopt="doc")
    assert a != b  # deux instances distinctes ne sont pas égales
    assert len({a, b}) == 2  # hachables


def test_pilotable_par_argv_explicite_sans_sys_argv(monkeypatch):
    """#24 : argv/nom explicites permettent d'exécuter hors d'un __main__.

    On casse `sys.argv` pour prouver qu'il n'est plus consulté.
    """
    monkeypatch.setattr(sys, "argv", ["NE-DOIT-PAS-ETRE-LU", "--introuvable"])
    reinitialise_configuration()

    capture = {}

    def main(_script=None):
        capture["script"] = _script
        return _script.arguments["--dry-run"]

    decoree = script_automatheque(DOC_OPTIONS, argv=["--dry-run"], nom="mon_module")(
        main
    )
    resultat = decoree()

    assert resultat is True
    assert capture["script"].nom_court == "mon_module"


# --- #5 : enrichissement de @script_automatheque -------------------------------


def test_dry_run_cable_automatiquement():
    """`--dry-run` déclaré dans l'usage → `_script.dry_run` reflète l'argument."""
    avec = execute_script(DOC_OPTIONS, _noop, argv=["--dry-run"])
    sans = execute_script(DOC_OPTIONS, _noop, argv=[])

    assert avec.script.dry_run is True
    assert sans.script.dry_run is False


def test_verbosite_v_descend_en_debug():
    """`-v` abaisse la **racine** en DEBUG (le handler racine est NOTSET)."""
    execute_script(DOC_OPTIONS, _noop, argv=["-v"])

    assert logging.getLogger().level == logging.DEBUG


def test_verbosite_q_remonte_en_warning():
    """`-q` masque les INFO en passant la **racine** en WARNING."""
    execute_script(DOC_OPTIONS, _noop, argv=["-q"])

    assert logging.getLogger().level == logging.WARNING


def test_interruption_clavier_sort_proprement_130():
    """Un Ctrl-C (KeyboardInterrupt) se traduit en `SystemExit(130)`."""

    def interrompt(_script=None):
        raise KeyboardInterrupt

    with pytest.raises(SystemExit) as exc:
        execute_script(DOC_OPTIONS, interrompt, argv=[])

    assert exc.value.code == 130


def test_exception_journalisee_et_propagee(capfd):
    """Une exception non gérée est journalisée (avec traceback) puis remonte.

    On capture stderr au niveau du descripteur (`capfd`) : `configure_logging`
    reconfigure la racine via dictConfig, ce qui remplacerait le handler de
    `caplog`.
    """

    def echoue(_script=None):
        raise ValueError("boom")

    with pytest.raises(ValueError, match="boom"):
        execute_script(DOC_OPTIONS, echoue, argv=[])

    err = capfd.readouterr().err
    assert "erreur" in err.lower()
    assert "Traceback" in err  # la traceback accompagne bien le message


def test_duree_mesuree_a_la_fin():
    """La fin de traitement dispose d'un horodatage de début pour la durée."""
    res = execute_script(DOC_OPTIONS, _noop, argv=[])
    assert res.script._debut is not None


# --- #39 : intégration commandopt (dispatch de sous-commandes) -----------------


#: Usage docopt déclarant deux sous-commandes + des options internes.
DOC_COMMANDES = """Script de démonstration des sous-commandes.

Usage:
  demo [--ajouter] [--supprimer] [--config=<f>] [-v] [--dry-run]

Options:
  --ajouter     Ajoute.
  --supprimer   Supprime.
  -v            Bavard.
  --dry-run     Simulation.
  --config=<f>  Configuration ponctuelle.
"""


def test_commande_est_l_alias_de_commandopt():
    """`commande` est exactement le décorateur `commandopt.commandopt`."""
    assert commande is commandopt.commandopt


def test_execute_commande_aiguille_vers_la_bonne_commande():
    """`execute_commande` sélectionne la commande selon les options présentes."""
    reg = Registry()

    @commande(["--ajouter"], registry=reg)
    def ajouter(arguments):
        return "AJOUT"

    @commande(["--supprimer"], registry=reg)
    def supprimer(arguments):
        return "SUPPR"

    def main(_script=None):
        return _script.execute_commande(registry=reg)

    assert execute_script(DOC_COMMANDES, main, argv=["--ajouter"]).resultat == "AJOUT"
    assert execute_script(DOC_COMMANDES, main, argv=["--supprimer"]).resultat == "SUPPR"


def test_execute_commande_ignore_les_options_internes():
    """`--config`/`-v`/`--dry-run` n'entrent pas dans la sélection, mais restent
    transmises à la commande."""
    reg = Registry()

    @commande(["--ajouter"], registry=reg)
    def ajouter(arguments):
        return arguments  # on renvoie le dict complet pour l'inspecter

    def main(_script=None):
        return _script.execute_commande(registry=reg)

    args = execute_script(
        DOC_COMMANDES,
        main,
        argv=["--ajouter", "--config", "c.ini", "-v", "--dry-run"],
    ).resultat

    # La sélection a réussi malgré les options internes…
    assert args["--ajouter"] is True
    # … et la commande reçoit bien le dict complet, options internes incluses.
    assert args["--config"] == "c.ini"


def test_execute_commande_sans_correspondance_leve():
    """Aucune option de commande présente → NoCommandFoundError (propagée)."""
    reg = Registry()

    @commande(["--ajouter"], registry=reg)
    def ajouter(arguments):
        return "AJOUT"

    def main(_script=None):
        return _script.execute_commande(registry=reg)

    with pytest.raises(NoCommandFoundError):
        execute_script(DOC_COMMANDES, main, argv=["--config", "c.ini"])


def test_options_internes_couvrent_les_commodites():
    """Le jeu d'options ignorées couvre config + dry-run + verbosité."""
    attendues = {"--config", "--dry-run", "-v", "--verbose", "-q", "--quiet"}
    assert attendues <= OPTIONS_INTERNES


# --- #4 : migration docopt -> docopt-ng ----------------------------------------


def test_parseur_est_docopt_ng():
    """#4 : le module `docopt` importé est fourni par docopt-ng (dépendance
    déclarée), aligné avec commandopt qui s'appuie sur le même parseur."""
    import importlib.metadata as md

    assert md.version("docopt-ng")  # lève PackageNotFoundError si absent
