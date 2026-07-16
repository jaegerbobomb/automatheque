"""Tests de la promotion de l'API script (#41).

`script_automatheque` / `script` / `ScriptAutomatheque` vivent désormais dans
`automatheque.script`. `automatheque.util.script` reste un shim de
rétrocompatibilité qui ré-exporte les mêmes objets et émet un
`DeprecationWarning` à l'import.
"""

import importlib
import warnings


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
