#!/usr/bin/python
# -*- coding: utf-8 -*-
"""Utilitaires de manipulation des structures classiques de python.

Divers utilitaires pour dict, list etc.
"""

import importlib.resources as res
from copy import deepcopy
from datetime import date, datetime, time, timezone
from functools import lru_cache
from typing import Dict, List
from zoneinfo import ZoneInfo


def dict_merge(a, b):
    """Merge récursif de 2 dictionnaires python.

    https://www.xormedia.com/recursively-merge-dictionaries-in-python/

    recursively merges dict's. not just simple a['key'] = b['key'], if
    both a and b have a key who's value is a dict then dict_merge is called
    on both values and the result stored in the returned dictionary.
    """
    if not isinstance(b, dict):
        return b
    result = deepcopy(a)
    for k, v in b.items():
        if k in result and isinstance(result[k], dict):
            result[k] = dict_merge(result[k], v)
        else:
            result[k] = deepcopy(v)
    return result


def date_en_datetime(
    date_src, time_obj=None, heures=0, minutes=0, secondes=0, tzinfo=timezone.utc
):
    """Parfois on reçoit une date et on veut la transformer en datetime.

    Si on ne précise rien, elle est définie pour la timezone UTC.

    :param date_src: date à transformer éventuellement en datetime (si elle ne
                     l'est pas déjà)
    :param time_obj: Objet datetime.time à utiliser pour compléter la date
                     defaut = None
    :param heures: si on n'envoie pas d'objet "time_obj" on peut donner ses
                   paramètres
    :param minutes: idem
    :param secondes: idem
    :param tzinfo: fuseau à appliquer, défaut ``datetime.timezone.utc``
    """
    date_conv = date_src
    if time_obj is None:
        time_obj = time(heures, minutes, secondes, tzinfo=tzinfo)
    elif date_est_naive(time_obj):
        # `time_obj` naïf : on lui attache le fuseau. (L'ancien
        # `tzinfo.localize(time_obj)` était un double piège pytz : API absente
        # de la stdlib, et résultat jeté sans affectation.)
        time_obj = time_obj.replace(tzinfo=tzinfo)
    if not isinstance(date_src, datetime) and isinstance(date_src, date):
        date_conv = datetime.combine(date_conv, time_obj)
    return date_conv


def date_est_naive(date_src):
    """Renvoie True si la date est naive (ie sans TZ), False sinon.

    Passe par ``date_src.utcoffset()`` (méthode de l'objet) et non
    ``date_src.tzinfo.utcoffset(date_src)`` : la première marche pour un
    ``datetime`` **comme** pour un ``time`` — un `time` n'a pas de date à
    fournir à `tzinfo.utcoffset`, et le `timezone` stdlib refuse alors
    l'argument (là où `pytz` l'ignorait silencieusement).
    """
    return date_src.utcoffset() is None


@lru_cache(maxsize=1)
def _pays_vers_fuseaux() -> Dict[str, List[str]]:
    """Mapping code pays ISO 3166 → fuseaux IANA, lu depuis ``tzdata``.

    ``zone1970.tab`` est la table de référence de la base IANA — celle dont
    ``pytz`` tirait lui-même son ``country_timezones``. Format d'une ligne :
    ``codes_pays<TAB>coordonnées<TAB>zone<TAB>commentaire`` ; ``codes_pays`` peut
    en lister plusieurs, séparés par des virgules (une même zone servant
    plusieurs pays). Le fichier est fourni par la dépendance ``tzdata`` — la
    même qui fournit les données ``zoneinfo`` sous Windows et en image *slim*.
    """
    texte = (
        res.files("tzdata.zoneinfo")
        .joinpath("zone1970.tab")
        .read_text(encoding="utf-8")
    )
    mapping: Dict[str, List[str]] = {}
    for ligne in texte.splitlines():
        if not ligne or ligne.startswith("#"):
            continue
        champs = ligne.split("\t")
        codes, zone = champs[0], champs[2]
        for code in codes.split(","):
            mapping.setdefault(code, []).append(zone)
    return mapping


def datetimezone_depuis_code_pays(date_src, code_pays):
    """Renvoie une datetime "aware" à partir d'un code pays.

    Si la date est déjà "aware", ne fait rien. Si elle est "naive", on prend le
    **premier** fuseau associé au code pays (comportement historique — arbitraire
    pour un pays à plusieurs fuseaux) et on l'y attache, sans décaler l'heure
    (l'heure murale est interprétée comme étant dans ce fuseau).

    :param date_src: datetime "naive" (sinon retourne date_src)
    :param code_pays: code du pays (ex: FR, JP)
    :return: datetime ou None si le code_pays est inconnu
    """
    if not date_est_naive(date_src):
        return date_src
    zones = _pays_vers_fuseaux().get(code_pays)
    if not zones:
        return None
    return date_src.replace(tzinfo=ZoneInfo(zones[0]))
