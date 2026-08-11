# -*- coding: utf-8 -*-
"""Durées humaines et humanisation relative — *politique* de saisie/présentation.

Ce module traite ce qu'un humain **écrit** (« 1h30 ») et ce qu'on lui
**réaffiche** (« il y a 5 min »). Ce sont des décisions d'application — langue,
seuils, arrondis, granularité — donc leur place est dans le cœur, pas dans le
vocabulaire de valeur (`automatheque.schema.temps`, #48). Les deux moitiés
n'ont **aucune dépendance** l'une envers l'autre : tant que
:func:`humanise_relatif` **reçoit** son instant de référence, ce module ignore
tout de #48. Cf. #132.

La **langue** est extériorisée dans :mod:`automatheque.util.langues` (#136) :
les trois fonctions prennent un paramètre ``langue`` — un code (« fr », « en »,
défaut « fr ») résolu par les points d'entrée, ou un objet :class:`~automatheque
.util.langues.Langue` passé en direct. `fr` et `en` sont fournis par le cœur ;
une langue de plus s'ajoute en installant un paquet qui la déclare.

Unités canoniques (structure, indépendante de la langue) : semaine (``w``),
jour (``d``), heure (``h``), minute (``m``), seconde (``s``). Les graphies
acceptées en entrée et les libellés émis en sortie, eux, dépendent de la langue.

Deux partis pris **explicites** (valables pour `fr` et `en`) :

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
from datetime import datetime, timedelta
from typing import Optional, Tuple, Union

from automatheque.exceptions import DureeInvalide
from automatheque.util.langues import (
    EN,
    FR,
    Langue,
    Vocabulaire,
    langues_disponibles,
    resout_langue,
)

# Ré-exports : `Langue`/`Vocabulaire`/`FR`/`EN` sont *le* vocabulaire des
# durées ; on les rend importables depuis `temps` (et donc `util`) pour que
# l'appelant n'ait pas à connaître le découpage interne temps/langues.
__all__ = [
    "parse_duree",
    "humanise_duree",
    "humanise_relatif",
    "parse_date_floue",
    "Langue",
    "Vocabulaire",
    "FR",
    "EN",
    "langues_disponibles",
    "resout_langue",
]

#: Nombre de secondes par unité canonique. Structure, non langue.
_SECONDES = {"w": 604800, "d": 86400, "h": 3600, "m": 60, "s": 1}

#: Unité immédiatement plus petite, pour le nombre nu implicite (``1h30``).
_SUIVANT_PLUS_PETIT = {"w": "d", "d": "h", "h": "m", "m": "s"}

# Un nombre (entier ou décimal) suivi, éventuellement, d'une « unité » : toute
# suite de caractères ni chiffre, ni espace, ni point. Volontairement *large* —
# on ne présume pas de l'alphabet de l'unité (une langue tierce peut en employer
# d'autres) : la validité est tranchée par la table d'alias de la langue, pas
# par ce motif.
_JETON = re.compile(r"(\d+(?:\.\d+)?)\s*([^\d\s.]*)")


def parse_duree(chaine: str, langue: Union[str, Langue] = "fr") -> timedelta:
    """Interprète une durée humaine et renvoie le :class:`~datetime.timedelta`.

    Accepte ``"1h30"``, ``"2d"``, ``"90s"``, ``"1h 30m"``, ``"1j2h"``… Les
    graphies reconnues dépendent de ``langue`` (``fr`` par défaut, qui tolère
    aussi l'anglais en entrée) ; les règles de composition, elles, sont
    structurelles et décrites en tête de module.

    :param langue: code (« fr », « en ») résolu par les points d'entrée, ou un
        objet :class:`~automatheque.util.langues.Langue` passé en direct.
    :raise DureeInvalide: chaîne vide, jeton mal formé, unité inconnue *dans
        cette langue*, unité « mois », ou nombre nu sans composante de référence.
    :raise LangueInconnue: si ``langue`` est un code non déclaré.
    """
    lang = resout_langue(langue)
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
        elif unite in lang.mois:
            raise DureeInvalide(
                "unité « mois » refusée dans {!r} : un mois n'est pas une durée "
                "fixe (utilisez des jours, ou une date)".format(chaine)
            )
        else:
            canonique = lang.alias.get(unite)
            if canonique is None:
                raise DureeInvalide(
                    "unité inconnue « {} » dans {!r} (langue {!r})".format(
                        unite, chaine, lang.code
                    )
                )

        total += float(nombre) * _SECONDES[canonique]
        precedente = canonique
        trouve = True

    if not trouve:
        raise DureeInvalide("aucune durée reconnue dans {!r}".format(chaine))
    return timedelta(seconds=total)


def humanise_duree(duree: timedelta, langue: Union[str, Langue] = "fr") -> str:
    """Rend une durée lisible : ``"1j 2h 30m 15s"`` (``"1d 2h…"`` en anglais).

    Granularité **la seconde** (les microsecondes sont arrondies). Décompose en
    jours/heures/minutes/secondes — pas en semaines, mais l'aller-retour reste
    exact : ``parse_duree(humanise_duree(timedelta(weeks=2)))`` vaut bien deux
    semaines (« 14j »). Une durée nulle donne ``"0s"``.

    L'inverse de :func:`parse_duree` (à langue égale) :
    ``parse_duree(humanise_duree(d, langue), langue) == d`` sur toute durée d'un
    nombre entier de secondes.

    :param langue: code ou objet :class:`~automatheque.util.langues.Langue` ;
        seuls ses libellés de sortie changent (``fr`` écrit ``d`` « j »).
    :raise ValueError: si ``duree`` est négative (le signe relève de
        :func:`humanise_relatif`, pas d'une durée en soi).
    """
    lang = resout_langue(langue)
    if duree < timedelta(0):
        raise ValueError("humanise_duree n'humanise pas une durée négative")
    restant = round(duree.total_seconds())
    morceaux = []
    for canonique in ("d", "h", "m", "s"):
        quantite, restant = divmod(restant, _SECONDES[canonique])
        if quantite:
            morceaux.append("{}{}".format(quantite, lang.libelles_duree[canonique]))
    return " ".join(morceaux) if morceaux else "0s"


def humanise_relatif(
    instant: datetime,
    *,
    maintenant: datetime,
    langue: Union[str, Langue] = "fr",
    vocabulaire: Optional[Vocabulaire] = None,
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

    :param langue: code ou objet :class:`~automatheque.util.langues.Langue` ;
        son :class:`~automatheque.util.langues.Vocabulaire` relatif est utilisé.
    :param vocabulaire: pour surcharger *uniquement* le vocabulaire relatif sans
        toucher au reste — un :class:`~automatheque.util.langues.Vocabulaire`
        (ou une :class:`~automatheque.util.langues.Langue`, dont on prend le
        ``relatif``). ``None`` (défaut) : on prend celui de ``langue``.
    :param seuil_instant: en deçà (en valeur absolue), on renvoie l'expression
        « à l'instant » plutôt qu'un « il y a 0 s ».
    """
    voc = _vocabulaire_relatif(vocabulaire, langue)
    ecart = (instant - maintenant).total_seconds()
    if abs(ecart) < seuil_instant.total_seconds():
        return voc.instant
    duree = _grossier(abs(ecart), voc.unites)
    modele = voc.futur if ecart > 0 else voc.passe
    return modele.format(duree=duree)


def _vocabulaire_relatif(
    vocabulaire: Union[Vocabulaire, Langue, None], langue: Union[str, Langue]
) -> Vocabulaire:
    """Détermine le vocabulaire relatif à employer.

    ``vocabulaire`` explicite l'emporte (un :class:`Vocabulaire`, ou une
    :class:`Langue` dont on extrait le ``relatif``) ; sinon on prend celui de
    ``langue``. Cette tolérance préserve les appels ``vocabulaire=…`` d'avant
    #136.
    """
    if vocabulaire is not None:
        if isinstance(vocabulaire, Langue):
            return vocabulaire.relatif
        if isinstance(vocabulaire, Vocabulaire):
            return vocabulaire
        raise TypeError(
            "vocabulaire doit être un Vocabulaire ou une Langue, pas {!r}".format(
                type(vocabulaire).__name__
            )
        )
    return resout_langue(langue).relatif


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
