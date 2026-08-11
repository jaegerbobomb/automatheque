# -*- coding: utf-8 -*-
"""Durées humaines et humanisation relative — *politique* de saisie/présentation.

Ce module traite ce qu'un humain **écrit** (« 1h30 ») et ce qu'on lui
**réaffiche** (« il y a 5 min »). Ce sont des décisions d'application — langue,
seuils, arrondis, granularité — donc leur place est dans le cœur, pas dans le
vocabulaire de valeur (`automatheque.schema.temps`, #48). Les deux moitiés
n'ont **aucune dépendance** l'une envers l'autre : tant que
:func:`humanise_relatif` **reçoit** son instant de référence, ce module ignore
tout de #48. Cf. #132.

Unités (au **parsing**, fr/en tolérés en entrée ; une seule forme émise) :

===========  =========================================  ========
canonique    alias acceptés                             émis par
                                                         humanise
===========  =========================================  ========
semaine      ``w`` ``sem`` ``semaine(s)`` ``week(s)``    (via jours)
jour         ``d`` ``j`` ``jour(s)`` ``day(s)``          ``j``
heure        ``h`` ``hr(s)`` ``heure(s)`` ``hour(s)``    ``h``
minute       ``m`` ``min(s)`` ``minute(s)``              ``m``
seconde      ``s`` ``sec(s)`` ``seconde(s)`` ``second``  ``s``
===========  =========================================  ========

Deux partis pris **explicites** :

* ``m`` vaut **toujours** une minute, jamais un mois. Un mois n'est pas une
  durée fixe — un :class:`~datetime.timedelta` ne peut pas le porter. Toute
  unité « mois » (``mo``, ``mois``, ``month(s)``) est donc **refusée**
  franchement (``DureeInvalide``) plutôt qu'approximée à 30 jours : le genre
  d'approximation qu'on découvre six mois plus tard sur un TTL.
* Un **nombre nu** qui suit une composante prend l'unité immédiatement plus
  petite : ``1h30`` → 1 h 30 min, ``1m30`` → 1 min 30 s. C'est l'écriture
  familière ``HhMM``. Sans composante précédente (« 90 » seul), c'est ambigu :
  refusé.

Un échec de parsing lève :class:`~automatheque.exceptions.DureeInvalide` (de la
hiérarchie ``AutomathequeBaseException``, et aussi ``ValueError``) — **jamais**
un ``None`` silencieux.
"""

import re
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Tuple

from automatheque.exceptions import DureeInvalide

#: Nombre de secondes par unité canonique.
_SECONDES = {"w": 604800, "d": 86400, "h": 3600, "m": 60, "s": 1}

#: Alias d'entrée (fr/en) → unité canonique.
_ALIAS = {
    "s": "s", "sec": "s", "secs": "s",
    "seconde": "s", "secondes": "s", "second": "s", "seconds": "s",
    "m": "m", "min": "m", "mins": "m", "minute": "m", "minutes": "m",
    "h": "h", "hr": "h", "hrs": "h",
    "heure": "h", "heures": "h", "hour": "h", "hours": "h",
    "d": "d", "j": "d", "jour": "d", "jours": "d", "day": "d", "days": "d",
    "w": "w", "sem": "w", "semaine": "w", "semaines": "w",
    "week": "w", "weeks": "w",
}  # fmt: skip

#: Unités « mois » refusées explicitement (durée non fixe).
_MOIS = frozenset({"mo", "mois", "month", "months"})

#: Unité immédiatement plus petite, pour le nombre nu implicite (``1h30``).
_SUIVANT_PLUS_PETIT = {"w": "d", "d": "h", "h": "m", "m": "s"}

#: Un nombre (entier ou décimal) suivi, éventuellement, d'une unité en lettres.
_JETON = re.compile(r"(\d+(?:\.\d+)?)\s*([a-zà-ÿ]*)")


def parse_duree(chaine: str) -> timedelta:
    """Interprète une durée humaine et renvoie le :class:`~datetime.timedelta`.

    Accepte ``"1h30"``, ``"2d"``, ``"90s"``, ``"1h 30m"``, ``"1j2h"``… Les
    unités et les règles de composition sont décrites en tête de module.

    :raise DureeInvalide: chaîne vide, jeton mal formé, unité inconnue, unité
        « mois », ou nombre nu sans composante de référence.
    """
    if not isinstance(chaine, str):
        raise DureeInvalide(
            "parse_duree attend une chaîne, pas {!r}".format(type(chaine).__name__)
        )
    texte = chaine.strip().lower()
    if not texte:
        raise DureeInvalide("durée vide")

    total = 0.0
    precedente = None
    position = 0
    trouve = False
    while position < len(texte):
        if texte[position].isspace():
            position += 1
            continue
        jeton = _JETON.match(texte, position)
        if jeton is None:
            raise DureeInvalide(
                "durée illisible à « {} » dans {!r}".format(texte[position:], chaine)
            )
        nombre, unite = jeton.groups()
        position = jeton.end()

        if unite == "":
            # Nombre nu : prend l'unité juste plus petite que la précédente.
            if precedente is None:
                raise DureeInvalide(
                    "nombre sans unité dans {!r} : ambigu (ex. « 90s »)".format(chaine)
                )
            canonique = _SUIVANT_PLUS_PETIT.get(precedente)
            if canonique is None:
                raise DureeInvalide(
                    "nombre nu après des secondes dans {!r} : "
                    "aucune unité plus fine".format(chaine)
                )
        elif unite in _MOIS:
            raise DureeInvalide(
                "unité « mois » refusée dans {!r} : un mois n'est pas une durée "
                "fixe (utilisez des jours, ou une date)".format(chaine)
            )
        else:
            canonique = _ALIAS.get(unite)
            if canonique is None:
                raise DureeInvalide(
                    "unité inconnue « {} » dans {!r}".format(unite, chaine)
                )

        total += float(nombre) * _SECONDES[canonique]
        precedente = canonique
        trouve = True

    if not trouve:
        raise DureeInvalide("aucune durée reconnue dans {!r}".format(chaine))
    return timedelta(seconds=total)


def humanise_duree(duree: timedelta) -> str:
    """Rend une durée lisible : ``"1j 2h 30m 15s"``.

    Granularité **la seconde** (les microsecondes sont arrondies). Décompose en
    jours/heures/minutes/secondes — pas en semaines, mais l'aller-retour reste
    exact : ``parse_duree(humanise_duree(timedelta(weeks=2)))`` vaut bien deux
    semaines (« 14j »). Une durée nulle donne ``"0s"``.

    L'inverse de :func:`parse_duree` : ``parse_duree(humanise_duree(d)) == d``
    sur toute durée d'un nombre entier de secondes.

    :raise ValueError: si ``duree`` est négative (le signe relève de
        :func:`humanise_relatif`, pas d'une durée en soi).
    """
    if duree < timedelta(0):
        raise ValueError("humanise_duree n'humanise pas une durée négative")
    restant = round(duree.total_seconds())
    morceaux = []
    for lettre in ("d", "h", "m", "s"):
        quantite, restant = divmod(restant, _SECONDES[lettre])
        if quantite:
            # `d` s'écrit `j` en sortie (francophone), tout en se parsant aussi.
            morceaux.append("{}{}".format(quantite, "j" if lettre == "d" else lettre))
    return " ".join(morceaux) if morceaux else "0s"


@dataclass(frozen=True)
class Vocabulaire:
    """Gabarits et libellés de :func:`humanise_relatif`.

    Français par défaut. Passer un autre ``Vocabulaire`` suffit à traduire, sans
    imposer une i18n complète. ``passe``/``futur`` reçoivent ``{duree}`` ;
    ``unites`` va du plus grand au plus petit, chaque libellé étant invariable
    (« 1 min », « 5 min ») pour éviter la gestion du pluriel.
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


#: Vocabulaire français, utilisé par défaut.
FR = Vocabulaire()


def humanise_relatif(
    instant: datetime,
    *,
    maintenant: datetime,
    vocabulaire: Vocabulaire = FR,
    seuil_instant: timedelta = timedelta(seconds=1),
) -> str:
    """Situe ``instant`` par rapport à ``maintenant`` : « il y a 5 min », « dans 2 j ».

    La fonction **reçoit** son instant de référence (``maintenant``,
    obligatoire et nommé) au lieu de lire l'horloge : elle reste ainsi testable
    et découplée de l'instant d'exécution — la leçon « recevoir plutôt que
    chercher ». Les deux ``datetime`` doivent partager la même conscience du
    fuseau (toutes deux *tz-aware*, cf. #48) ; ce module ne stampe rien.

    L'affichage est **grossier** : une seule unité, la plus grande atteinte,
    arrondie. Il monte jusqu'à la semaine puis reste en semaines — pas de
    « mois » approximatif (même principe que :func:`parse_duree`).

    :param seuil_instant: en deçà (en valeur absolue), on renvoie ``instant``
        (« à l'instant ») plutôt qu'un « il y a 0 s ».
    :param vocabulaire: gabarits et libellés ; voir :class:`Vocabulaire`.
    """
    ecart = (instant - maintenant).total_seconds()
    if abs(ecart) < seuil_instant.total_seconds():
        return vocabulaire.instant
    duree = _grossier(abs(ecart), vocabulaire.unites)
    modele = vocabulaire.futur if ecart > 0 else vocabulaire.passe
    return modele.format(duree=duree)


def _grossier(secondes: float, unites: Tuple[Tuple[str, int], ...]) -> str:
    """Exprime ``secondes`` avec la plus grande unité atteinte, arrondie."""
    for libelle, taille in unites:
        if secondes >= taille:
            return "{} {}".format(round(secondes / taille), libelle)
    return "0 {}".format(unites[-1][0])


def parse_date_floue(texte: str, **kwargs) -> datetime:
    """Interprète une date écrite « à la main », via l'extra ``automatheque[dates]``.

    S'appuie sur ``dateutil`` — importé **paresseusement**, au moment de
    l'appel, pour garder le cœur léger (précédent : ``vobject`` dans
    ``automatheque.schema[calendrier]``). Sans l'extra, le paquet s'importe et
    tout le reste fonctionne ; seul cet appel lève un ``ImportError`` nommant
    l'extra.

    Hors périmètre ici : la normalisation de fuseau. ``dateutil`` peut renvoyer
    une ``datetime`` naïve ; c'est à l'appelant (ou à #48) de la rendre
    *tz-aware*. Les ``kwargs`` sont transmis tels quels à ``dateutil``.

    :raise ImportError: si l'extra ``dates`` n'est pas installé.
    """
    try:
        # `dateutil` (extra optionnel) n'expose pas de stubs : mypy le tolère
        # via `ignore_missing_imports` quand il est absent (cas de la CI), et
        # on neutralise `import-untyped` pour le développeur qui a l'extra.
        from dateutil import parser as _parser  # type: ignore[import-untyped]
    except ImportError as exc:  # pragma: no cover - dépend de l'installation
        raise ImportError(
            "Le parsing de dates floues réclame dateutil : "
            'pip install "automatheque[dates]"'
        ) from exc
    return _parser.parse(texte, **kwargs)
