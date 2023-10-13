#!/usr/bin/python
# -*- coding: utf-8 -*-
"""Utilitaires de manipulation des structures classiques de python.

Divers utilitaires pour dict, list etc.
"""
from copy import deepcopy
from datetime import date, datetime, time

import pytz


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
    date_src, time_obj=None, heures=0, minutes=0, secondes=0, tzinfo=pytz.utc
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
    :param tzinfo: Objet pytz timezone, defaut à pytz.utc
    """
    date_conv = date_src
    if time_obj is None:
        time_obj = time(heures, minutes, secondes, tzinfo=tzinfo)
    elif time_obj is not None and date_est_naive(time_obj):
        tzinfo.localize(time_obj)
    if not isinstance(date_src, datetime) and isinstance(date_src, date):
        date_conv = datetime.combine(date_conv, time_obj)
    return date_conv


def date_est_naive(date_src):
    """Renvoie True si la date est naive (ie sans TZ), False sinon."""
    if date_src.tzinfo is not None and date_src.tzinfo.utcoffset(date_src) is not None:
        return False
    return True


def datetimezone_depuis_code_pays(date_src, code_pays):
    """Renvoie une datetime "aware" à partir d'un code pays.

    Si la date est déjà "aware", ne fait rien. Si la date est bien "naive" en
    revanche, on cherche la première timezone associée au code pays, et on
    l'ajoute à la datetime.

    :param date_src: datetime "naive" (sinon retourne date_src)
    :param code_pays: code du pays (ex: FR, JP)
    :return: datetime ou None si le code_pays est invalide
    """
    if not date_est_naive(date_src):
        return date_src

    try:
        codes = pytz.country_timezones[code_pays]
    except KeyError:
        return None
    else:
        return pytz.timezone(codes[0]).localize(date_src)
