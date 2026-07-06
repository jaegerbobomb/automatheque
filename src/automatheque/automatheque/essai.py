# -*- coding: utf-8 -*-
"""Harness de test pour les scripts ``@script_automatheque``.

Tester un script décoré demanderait sinon de bricoler ``sys.argv``, la
configuration et le logger à la main. Ce module permet d'exécuter un script
décoré avec un ``argv`` contrôlé et d'inspecter l'objet
:class:`~automatheque.util.script.ScriptAutomatheque` produit (arguments parsés,
configuration chargée) ainsi que la valeur de retour.

Exemple ::

    from automatheque.essai import execute_script

    DOC = '''Mon script.

    Usage:
      prog [--action] [--config=<fichier>]

    Options:
      --action            Réalise l'action.
      --config=<fichier>  Fichier de configuration.
    '''

    def main(_script=None):
        return _script.arguments["--action"]

    resultat, script = execute_script(DOC, main, argv=["--action"])
    assert resultat is True
    assert script.arguments["--action"] is True
"""

import sys
from collections import namedtuple
from pathlib import Path

from automatheque.configuration import charge_configuration
from automatheque.util.script import script_automatheque

__all__ = [
    "ResultatScript",
    "execute_script",
    "reinitialise_configuration",
    "ecris_config",
]

#: Valeur de retour de :func:`execute_script` : ``(resultat, script)``.
ResultatScript = namedtuple("ResultatScript", ["resultat", "script"])


def reinitialise_configuration():
    """Oublie la configuration globale mise en cache par ``charge_configuration``.

    Utile entre deux tests : ``charge_configuration`` mémorise son résultat dans
    un attribut de fonction, qui fuiterait sinon d'un test à l'autre.
    """
    if hasattr(charge_configuration, "config"):
        del charge_configuration.config


def ecris_config(chemin, contenu):
    """Écrit ``contenu`` (un ``.ini``) dans ``chemin`` ; renvoie le chemin (str).

    Pratique avec le ``tmp_path`` de pytest pour fabriquer une configuration
    jetable à passer via ``argv=["--config", chemin]``.
    """
    chemin = Path(chemin)
    chemin.write_text(contenu, encoding="utf-8")
    return str(chemin)


def execute_script(doc, fonction, argv=None, version=None, reinitialise=True):
    """Décore ``fonction`` avec ``script_automatheque`` et l'exécute avec ``argv``.

    :param doc: la chaîne d'usage docopt (le ``__doc__`` du script).
    :param fonction: la fonction à décorer ; elle doit accepter ``_script``.
    :param argv: arguments de ligne de commande (sans le nom du programme).
    :param version: version éventuelle passée à docopt.
    :param reinitialise: si vrai (défaut), oublie la configuration en cache avant
        l'exécution, pour isoler les tests les uns des autres.
    :return: un :class:`ResultatScript` ``(resultat, script)`` où ``resultat`` est
        la valeur renvoyée par ``fonction`` et ``script`` l'objet
        :class:`~automatheque.util.script.ScriptAutomatheque` (``.arguments``,
        ``.config``…).
    """
    if reinitialise:
        reinitialise_configuration()

    capture = {}

    def fonction_capturante(*args, _script=None, **kwds):
        capture["script"] = _script
        return fonction(*args, _script=_script, **kwds)

    # `script_automatheque` lit sys.argv et charge la config dès la décoration,
    # d'où le pilotage de sys.argv autour de cette ligne.
    faux_argv = ["script-de-test", *(argv or [])]
    ancien_argv = sys.argv
    sys.argv = faux_argv
    try:
        decoree = script_automatheque(doc, version)(fonction_capturante)
        resultat = decoree()
    finally:
        sys.argv = ancien_argv

    return ResultatScript(resultat=resultat, script=capture.get("script"))
