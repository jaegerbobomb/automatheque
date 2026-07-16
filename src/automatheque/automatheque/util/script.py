# -*- coding:utf-8 -*-
"""Shim de rétrocompatibilité — l'API a déménagé vers :mod:`automatheque.script`.

``script_automatheque`` (son alias court ``script``) et ``ScriptAutomatheque``
vivent désormais dans :mod:`automatheque.script` (#41) : c'est l'API phare du
projet (« se faciliter le scripting »), elle n'a plus sa place parmi les
utilitaires bas niveau de ``util`` (``fichier``, ``reessaye``, ``repertoire``…).

Ce module reste importable pour ne pas casser le code existant, mais émet un
``DeprecationWarning`` à l'import. Migrez vos imports :

    - from automatheque.util.script import script      # déprécié
    + from automatheque.script import script

Le shim sera supprimé dans une version ultérieure.
"""

import warnings

from automatheque.script import (  # noqa: F401  (ré-exports voulus)
    ScriptAutomatheque,
    script,
    script_automatheque,
)

warnings.warn(
    "automatheque.util.script est déprécié : importez depuis "
    "automatheque.script (« from automatheque.script import script »). "
    "Ce shim sera supprimé dans une version ultérieure.",
    DeprecationWarning,
    stacklevel=2,
)

__all__ = ["script_automatheque", "ScriptAutomatheque", "script"]
