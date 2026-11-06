# -*- coding: utf-8 -*-
"""Évaluation des conditions de gabarit.

Une condition est une expression booléenne écrite dans la configuration,
formatée avec les champs de l'objet à renommer avant d'être évaluée :

```ini
r5 = ['{date.year}/{date:%%Y-%%m-%%d} @{ville} {pays}/{nom}',
      '"{date}" and "{ville}" and "{pays}" != "FR"', 3]
```

Une fois formatée, la condition ci-dessus devient
``'"2013-03-17" and "Osaka" and "JP" != "FR"'``.

Le code d'origine passait cette chaîne à `eval()`. Or les champs qui y sont
injectés viennent des **métadonnées des fichiers traités** — un album, un nom
de ville, une description. Un fichier soigneusement nommé suffisait donc à
faire exécuter du code arbitraire par un simple rangement de photos.

L'évaluation est ici faite sur l'arbre syntaxique, avec une liste blanche de
nœuds : des littéraux, `and` / `or` / `not`, des comparaisons, et l'appel de
quelques fonctions pures (`FONCTIONS_AUTORISEES` : `len`, `int`). Rien
d'autre. La syntaxe des conditions existantes est inchangée ; au pire, une
chaîne malveillante fait maintenant échouer la condition au lieu de sortir de
son bac à sable.
"""

import ast
from typing import Any

from .exceptions import ConditionInvalide

# Nœuds acceptés dans une condition. Tout ce qui appelle, importe, indexe,
# accède à un attribut ou nomme une variable en est absent — volontairement.
_NOEUDS_AUTORISES = (
    ast.Expression,
    ast.BoolOp,
    ast.And,
    ast.Or,
    ast.UnaryOp,
    ast.Not,
    ast.Compare,
    ast.Eq,
    ast.NotEq,
    ast.Lt,
    ast.LtE,
    ast.Gt,
    ast.GtE,
    ast.In,
    ast.NotIn,
    ast.Constant,
    ast.Tuple,
    ast.List,
    ast.Load,
)


# Fonctions qu'une condition peut appeler — pures, sur des littéraux :
# compter des épisodes (`len({episodes}) == 2`), comparer un numéro de disque
# (`int({disque}) > 1`). Appelées par leur nom, avec un seul argument.
FONCTIONS_AUTORISEES = {"len": len, "int": int}


def _appels_autorises(arbre) -> set:
    """Les nœuds `Name` qui désignent une fonction autorisée, appelée
    correctement ; tout autre `Call` ou `Name` reste refusé."""
    noms = set()
    for noeud in ast.walk(arbre):
        if (
            isinstance(noeud, ast.Call)
            and isinstance(noeud.func, ast.Name)
            and noeud.func.id in FONCTIONS_AUTORISEES
            and len(noeud.args) == 1
            and not noeud.keywords
            and not isinstance(noeud.args[0], ast.Starred)
        ):
            noms.add(id(noeud.func))
    return noms


def evalue_condition(condition: str) -> Any:
    """Évalue une condition déjà formatée, sans jamais exécuter de code.

    :param condition: expression booléenne composée de littéraux
    :raise ConditionInvalide: si l'expression est mal formée, ou si elle
                              contient autre chose que des littéraux, des
                              opérateurs booléens et des comparaisons
    """
    try:
        arbre = ast.parse(condition, mode="eval")
    except SyntaxError as exc:
        raise ConditionInvalide(condition, "expression mal formée") from exc

    appels = _appels_autorises(arbre)
    for noeud in ast.walk(arbre):
        if isinstance(noeud, ast.Name) and id(noeud) in appels:
            continue
        if isinstance(noeud, ast.Call) and id(noeud.func) in appels:
            continue
        if not isinstance(noeud, _NOEUDS_AUTORISES):
            raise ConditionInvalide(
                condition,
                "{} n'est pas autorisé dans une condition".format(type(noeud).__name__),
            )

    # À ce stade l'arbre ne contient que des littéraux, des opérateurs et des
    # appels aux seules `FONCTIONS_AUTORISEES` : rien d'autre n'est nommable.
    return eval(
        compile(arbre, "<condition>", "eval"),
        {"__builtins__": {}},
        dict(FONCTIONS_AUTORISEES),
    )
