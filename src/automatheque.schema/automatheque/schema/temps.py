# -*- coding: utf-8 -*-
"""Primitives de temps : des *value objects*, en stdlib pure.

Pourquoi ici, dans `schema`, et pas dans le cœur ? `schema` est une **feuille**
du graphe de dépendances (cf. #42) : il ne peut pas importer le cœur. Or les
primitives « valeur » du temps — « maintenant en UTC », « cette date, en
datetime » — ont le **même sens partout** et doivent être atteignables par tous
les paquets : leur place est dans la feuille. La *grammaire de présentation et
de saisie* (humanisation « il y a 5 min », parsing de durées), elle, est un
choix d'application et vit dans le cœur (#132). Cf. #48.

Tout est stdlib (`datetime`, `zoneinfo`) : aucune dépendance ajoutée, `schema`
reste installable avec le seul `attrs`.
"""

from datetime import date, datetime, time, timedelta, tzinfo
from typing import Iterator, Optional
from zoneinfo import ZoneInfo

#: UTC **nommé**. On préfère ``ZoneInfo("UTC")`` à ``datetime.timezone.utc`` :
#: ce dernier est un décalage fixe **sans nom**, et un sérialiseur qui doit
#: écrire un identifiant de fuseau s'y étrangle — vobject lève
#: ``Unable to guess TZID``. ``ZoneInfo("UTC")`` porte la clé « UTC » et se
#: sérialise proprement (en ``Z`` pour iCalendar) : un consommateur n'a donc
#: plus à contourner le cas UTC.
UTC = ZoneInfo("UTC")


def maintenant() -> datetime:
    """Horodatage courant, **tz-aware** (UTC).

    Un ``datetime`` conscient du fuseau évite les ambiguïtés au formatage et les
    comparaisons hasardeuses avec des dates naïves.
    """
    return datetime.now(UTC)


def est_naive(valeur) -> bool:
    """Vrai si ``valeur`` (un ``datetime`` **ou** un ``time``) n'a pas de fuseau.

    Passe par ``valeur.utcoffset()`` — qui marche pour un ``time`` comme pour un
    ``datetime`` — plutôt que ``valeur.tzinfo.utcoffset(valeur)``, qui exige un
    ``datetime`` (un ``time`` n'a pas de date à fournir).
    """
    return valeur.utcoffset() is None


def en_datetime(valeur, *, suppose: Optional[tzinfo] = None) -> datetime:
    """Ramène une ``date`` (ou une ``datetime``) à une ``datetime`` **tz-aware**.

    Une ``date`` nue devient minuit du jour. Une entrée **naïve** (date nue, ou
    ``datetime`` sans fuseau) exige un fuseau à **supposer** via ``suppose=`` :
    le helper ne stampe **jamais** un fuseau en douce (une date EXIF, par
    exemple, est locale, pas UTC — c'est à l'appelant de trancher). Une
    ``datetime`` déjà *aware* est renvoyée telle quelle.

    :param suppose: fuseau à attribuer à une entrée naïve (p. ex. :data:`UTC`).
    :raise TypeError: si ``valeur`` n'est ni une ``date`` ni une ``datetime``.
    :raise ValueError: si l'entrée est naïve et qu'aucun ``suppose=`` n'est donné.
    """
    if isinstance(valeur, datetime):
        dt = valeur
    elif isinstance(valeur, date):
        dt = datetime.combine(valeur, time(0, 0))
    else:
        raise TypeError(
            "en_datetime attend une date ou une datetime, pas {!r}".format(
                type(valeur).__name__
            )
        )
    if est_naive(dt):
        if suppose is None:
            raise ValueError(
                "entrée naïve : précisez le fuseau à supposer via `suppose=` "
                "(p. ex. `suppose=automatheque.schema.temps.UTC`)."
            )
        dt = dt.replace(tzinfo=suppose)
    return dt


def debut_de_jour(dt: datetime) -> datetime:
    """Minuit du jour de ``dt`` (fuseau conservé)."""
    return dt.replace(hour=0, minute=0, second=0, microsecond=0)


def debut_de_semaine(dt: datetime, *, premier_jour: int = 0) -> datetime:
    """Minuit du premier jour de la semaine contenant ``dt``.

    :param premier_jour: ``0`` = lundi (défaut, convention ISO), ``6`` = dimanche.
    """
    decalage = (dt.weekday() - premier_jour) % 7
    return debut_de_jour(dt - timedelta(days=decalage))


def debut_de_mois(dt: datetime) -> datetime:
    """Minuit du 1er du mois de ``dt``."""
    return debut_de_jour(dt.replace(day=1))


def arrondi(dt: datetime, pas: timedelta) -> datetime:
    """Arrondit ``dt`` au multiple de ``pas`` le plus proche, compté depuis minuit.

    Ainsi ``arrondi(dt, timedelta(minutes=15))`` cale sur le quart d'heure.
    L'arithmétique est *murale* (on ajoute/retranche à l'heure affichée) — sans
    incidence hors des rares bascules d'heure d'été intra-journée.

    :raise ValueError: si ``pas`` <= 0.
    """
    if pas <= timedelta(0):
        raise ValueError("pas doit être > 0")
    minuit = debut_de_jour(dt)
    ecoule = (dt - minuit).total_seconds()
    pas_s = pas.total_seconds()
    n = round(ecoule / pas_s)
    return minuit + timedelta(seconds=n * pas_s)


def intervalle(debut: datetime, fin: datetime, pas: timedelta) -> Iterator[datetime]:
    """Génère ``debut``, ``debut + pas``, … tant que c'est **avant** ``fin``.

    :raise ValueError: si ``pas`` <= 0.
    """
    if pas <= timedelta(0):
        raise ValueError("pas doit être > 0")
    courant = debut
    while courant < fin:
        yield courant
        courant += pas
