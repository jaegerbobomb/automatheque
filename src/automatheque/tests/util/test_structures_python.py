# -*- coding: utf-8 -*-
"""Tests des utilitaires sur les structures python (util/structures_python.py)."""

from datetime import date, datetime, time

import pytz
from automatheque.util.structures_python import (
    date_en_datetime,
    date_est_naive,
    datetimezone_depuis_code_pays,
    dict_merge,
)


def test_dict_merge_fusionne_recursivement():
    """Les sous-dictionnaires sont fusionnés récursivement, pas écrasés."""
    a = {"x": 1, "sous": {"a": 1, "b": 2}}
    b = {"y": 2, "sous": {"b": 20, "c": 30}}
    resultat = dict_merge(a, b)
    assert resultat == {"x": 1, "y": 2, "sous": {"a": 1, "b": 20, "c": 30}}


def test_dict_merge_ne_modifie_pas_les_sources():
    """La fusion travaille sur des copies profondes : les sources restent intactes."""
    a = {"sous": {"a": 1}}
    b = {"sous": {"b": 2}}
    dict_merge(a, b)
    assert a == {"sous": {"a": 1}}
    assert b == {"sous": {"b": 2}}


def test_dict_merge_b_non_dict_remplace_a():
    """Si b n'est pas un dict, il remplace intégralement a."""
    assert dict_merge({"a": 1}, "valeur") == "valeur"


def test_date_est_naive_vrai_pour_date_sans_tz():
    """Une datetime sans timezone est considérée comme naive."""
    assert date_est_naive(datetime(2020, 1, 1, 12, 0)) is True


def test_date_est_naive_faux_pour_date_avec_tz():
    """Une datetime avec timezone n'est pas naive."""
    aware = pytz.utc.localize(datetime(2020, 1, 1, 12, 0))
    assert date_est_naive(aware) is False


def test_date_en_datetime_convertit_une_date():
    """Une date pure est transformée en datetime (minuit UTC par défaut)."""
    resultat = date_en_datetime(date(2020, 5, 4))
    assert isinstance(resultat, datetime)
    assert resultat.year == 2020 and resultat.month == 5 and resultat.day == 4
    assert resultat.hour == 0 and resultat.minute == 0
    assert not date_est_naive(resultat)


def test_date_en_datetime_avec_heures_personnalisees():
    """Les paramètres heures/minutes/secondes complètent la date."""
    resultat = date_en_datetime(date(2020, 5, 4), heures=10, minutes=30, secondes=15)
    assert resultat.hour == 10 and resultat.minute == 30 and resultat.second == 15


def test_date_en_datetime_avec_time_obj_fourni():
    """Un objet time "aware" fourni est combiné avec la date."""
    time_obj = time(8, 15, 0, tzinfo=pytz.utc)
    resultat = date_en_datetime(date(2021, 3, 2), time_obj=time_obj)
    assert resultat.hour == 8 and resultat.minute == 15


def test_date_en_datetime_datetime_deja_convertie_inchangee():
    """Une datetime en entrée n'est pas reconvertie."""
    src = datetime(2019, 12, 31, 23, 59)
    assert date_en_datetime(src) is src


def test_datetimezone_depuis_code_pays_ajoute_la_tz():
    """Une datetime naive reçoit la première timezone du pays."""
    resultat = datetimezone_depuis_code_pays(datetime(2020, 1, 1, 10, 0), "FR")
    assert resultat is not None
    assert not date_est_naive(resultat)
    assert resultat.utcoffset().total_seconds() == 3600  # UTC+1 en hiver


def test_datetimezone_depuis_code_pays_date_deja_aware_inchangee():
    """Une datetime déjà "aware" est renvoyée telle quelle."""
    aware = pytz.utc.localize(datetime(2020, 1, 1, 10, 0))
    assert datetimezone_depuis_code_pays(aware, "FR") is aware


def test_datetimezone_depuis_code_pays_invalide_renvoie_none():
    """Un code pays inconnu renvoie None."""
    assert datetimezone_depuis_code_pays(datetime(2020, 1, 1), "ZZ") is None
