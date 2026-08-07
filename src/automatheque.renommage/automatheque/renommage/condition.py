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
nœuds : des littéraux, `and` / `or` / `not`, et des comparaisons. Rien
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

    for noeud in ast.walk(arbre):
        if not isinstance(noeud, _NOEUDS_AUTORISES):
            raise ConditionInvalide(
                condition,
                "{} n'est pas autorisé dans une condition".format(type(noeud).__name__),
            )

    # À ce stade l'arbre ne contient que des littéraux et des opérateurs :
    # `eval` n'a plus rien à se mettre sous la dent.
    return eval(compile(arbre, "<condition>", "eval"), {"__builtins__": {}}, {})
