# -*- coding: utf-8 -*-
"""Langues des durées : contrat `Langue` et registre par points d'entrée (#136).

Une **langue** rassemble tout ce dont :mod:`automatheque.util.temps` a besoin
pour *lire* (« 1h30 ») et *réafficher* (« il y a 5 min ») une durée dans une
langue donnée : la table d'alias d'entrée, les unités « mois » refusées, les
libellés de sortie, et le vocabulaire de l'humanisation relative.

Le cœur n'a **aucun chemin privilégié** : il fournit `fr` et `en`, mais les
déclare — comme n'importe quel paquet tiers — sur le groupe de points d'entrée
``automatheque.langues`` (voir son ``pyproject``). Le registre est *exactement*
l'union de ces points d'entrée ; le cœur est ainsi son propre premier
consommateur du mécanisme (réutilisé de #129), ce qui l'éprouve dès le départ.
Une application qui veut une langue de plus installe un paquet qui la déclare —
ou passe directement un objet :class:`Langue`, sans aucun greffon.

La découverte est **paresseuse** et mémoïsée : aucun coût à l'import, on ne
scanne les métadonnées qu'au premier accès par code.
"""

from dataclasses import dataclass, field
from functools import lru_cache
from importlib.metadata import entry_points
from typing import Dict, FrozenSet, List, Mapping, Tuple, Union

from automatheque.exceptions import LangueInconnue

# Groupe de points d'entrée où le cœur — et tout paquet tiers — déclare ses
# langues. Volontairement distinct de `automatheque.greffons` (#129) : une
# langue est une donnée statique, pas un greffon activable (identifiant, actif,
# registre d'instances). On réutilise le *mécanisme* de découverte, pas la
# classe `Greffon`.
GROUPE_LANGUES = "automatheque.langues"


@dataclass(frozen=True)
class Vocabulaire:
    """Gabarits et libellés de l'humanisation relative.

    ``passe``/``futur`` reçoivent ``{duree}`` ; ``unites`` va du plus grand au
    plus petit, chaque libellé étant invariable (« 1 min », « 5 min ») pour
    éviter la gestion du pluriel. C'est la moitié « présentation relative »
    d'une :class:`Langue` ; on peut aussi le passer seul à
    :func:`automatheque.util.temps.humanise_relatif`.
    """

    instant: str = "à l'instant"
    passe: str = "il y a {duree}"
    futur: str = "dans {duree}"
    unites: Tuple[Tuple[str, int], ...] = field(
        default=(
            ("sem", 604800),
            ("j", 86400),
            ("h", 3600),
            ("min", 60),
            ("s", 1),
        )
    )


@dataclass(frozen=True)
class Langue:
    """Tout ce qu'une langue apporte à :mod:`automatheque.util.temps`.

    :param code: identifiant court (« fr », « en »), tel que déclaré en point
        d'entrée.
    :param alias: table *mot → unité canonique* (``w``/``d``/``h``/``m``/``s``)
        pour le parsing. Une même langue peut tolérer plusieurs graphies, voire
        une autre langue en entrée (`fr` accepte l'anglais, cf. #132).
    :param mois: unités « mois » **refusées** explicitement (un mois n'est pas
        une durée fixe).
    :param libelles_duree: *unité canonique → libellé émis* par
        ``humanise_duree`` (fr écrit ``d`` « j », en écrit ``d`` « d »).
    :param relatif: le :class:`Vocabulaire` de l'humanisation relative.
    """

    code: str
    alias: Mapping[str, str]
    mois: FrozenSet[str]
    libelles_duree: Mapping[str, str]
    relatif: Vocabulaire = field(default_factory=Vocabulaire)


# --- Alias partagés ---------------------------------------------------------

# Table d'alias commune à `fr` et `en` : le dépôt est francophone mais les
# durées en configuration s'écrivent souvent à l'anglaise, donc les deux
# langues tolèrent les deux graphies en **entrée** (elles ne diffèrent qu'à la
# **sortie**). Reprend la table de #132 à l'identique, d'où la rétro-compat du
# parsing par défaut.
_ALIAS_FR_EN: Dict[str, str] = {
    "s": "s", "sec": "s", "secs": "s",
    "seconde": "s", "secondes": "s", "second": "s", "seconds": "s",
    "m": "m", "min": "m", "mins": "m", "minute": "m", "minutes": "m",
    "h": "h", "hr": "h", "hrs": "h",
    "heure": "h", "heures": "h", "hour": "h", "hours": "h",
    "d": "d", "j": "d", "jour": "d", "jours": "d", "day": "d", "days": "d",
    "w": "w", "sem": "w", "semaine": "w", "semaines": "w",
    "week": "w", "weeks": "w",
}  # fmt: skip

# Unités « mois » refusées (durée non fixe) — fr et en confondus.
_MOIS: FrozenSet[str] = frozenset({"mo", "mois", "month", "months"})


#: Français — tolère l'anglais en entrée, émet en français (``d`` → « j »).
FR = Langue(
    code="fr",
    alias=_ALIAS_FR_EN,
    mois=_MOIS,
    libelles_duree={"d": "j", "h": "h", "m": "m", "s": "s"},
    relatif=Vocabulaire(),
)

#: Anglais — mêmes alias en entrée, mais sortie et relatif anglophones.
EN = Langue(
    code="en",
    alias=_ALIAS_FR_EN,
    mois=_MOIS,
    libelles_duree={"d": "d", "h": "h", "m": "m", "s": "s"},
    relatif=Vocabulaire(
        instant="just now",
        passe="{duree} ago",
        futur="in {duree}",
        unites=(
            ("w", 604800),
            ("d", 86400),
            ("h", 3600),
            ("min", 60),
            ("s", 1),
        ),
    ),
)


# --- Registre par points d'entrée -------------------------------------------


@lru_cache(maxsize=1)
def _registre() -> Dict[str, Langue]:
    """Construit — une seule fois — le registre code → :class:`Langue`.

    Purement l'union des points d'entrée du groupe ``automatheque.langues`` :
    le cœur y déclare `fr`/`en`, les tiers leurs langues. Mémoïsé ; en cas
    d'installation d'un paquet en cours d'exécution, appeler
    ``_registre.cache_clear()`` (ce que font les tests de découverte).
    """
    registre: Dict[str, Langue] = {}
    for point in entry_points(group=GROUPE_LANGUES):
        registre[point.name] = point.load()
    return registre


def langues_disponibles() -> List[str]:
    """Codes de langue actuellement résolubles (points d'entrée découverts)."""
    return sorted(_registre())


def resout_langue(langue: Union[str, Langue]) -> Langue:
    """Résout une langue passée en **code** ou en **objet**.

    Un objet :class:`Langue` est renvoyé tel quel (aucun greffon requis). Un
    code est cherché dans le registre des points d'entrée.

    :raise LangueInconnue: si le code n'est déclaré par aucun point d'entrée.
    :raise TypeError: si ``langue`` n'est ni une chaîne ni une :class:`Langue`.
    """
    if isinstance(langue, Langue):
        return langue
    if isinstance(langue, str):
        try:
            return _registre()[langue]
        except KeyError:
            raise LangueInconnue(langue, disponibles=langues_disponibles()) from None
    raise TypeError(
        "langue doit être un code (str) ou un objet Langue, pas {!r}".format(
            type(langue).__name__
        )
    )
