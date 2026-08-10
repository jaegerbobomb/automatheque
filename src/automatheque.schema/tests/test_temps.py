# -*- coding: utf-8 -*-
"""Tests des primitives de temps (`schema.temps`, #48)."""

from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

import pytest
from automatheque.schema.temps import (
    UTC,
    arrondi,
    debut_de_jour,
    debut_de_mois,
    debut_de_semaine,
    en_datetime,
    est_naive,
    intervalle,
    maintenant,
)


def test_maintenant_est_tz_aware_utc():
    m = maintenant()
    assert m.tzinfo is not None
    assert m.utcoffset() == timedelta(0)


def test_utc_est_nomme():
    # Un UTC *nommé* (clé "UTC"), pas le décalage fixe anonyme `timezone.utc` —
    # c'est ce qui permet à un sérialiseur (vobject) d'écrire un TZID / `Z`.
    assert UTC.key == "UTC"


def test_est_naive_datetime_et_time():
    assert est_naive(datetime(2020, 1, 1, 12, 0)) is True
    assert est_naive(datetime(2020, 1, 1, 12, 0, tzinfo=UTC)) is False
    assert est_naive(time(12, 0)) is True
    assert est_naive(time(12, 0, tzinfo=UTC)) is False


def test_en_datetime_date_nue_exige_un_fuseau():
    with pytest.raises(ValueError):
        en_datetime(date(2020, 5, 4))  # naïve, sans suppose=
    dt = en_datetime(date(2020, 5, 4), suppose=UTC)
    assert dt == datetime(2020, 5, 4, 0, 0, tzinfo=UTC)


def test_en_datetime_naive_sans_suppose_leve():
    with pytest.raises(ValueError):
        en_datetime(datetime(2020, 5, 4, 12, 0))


def test_en_datetime_naive_avec_suppose():
    dt = en_datetime(datetime(2020, 5, 4, 12, 0), suppose=ZoneInfo("Europe/Paris"))
    assert not est_naive(dt)
    assert dt.utcoffset() == timedelta(hours=2)  # CEST en mai


def test_en_datetime_aware_inchangee():
    src = datetime(2020, 5, 4, 12, 0, tzinfo=UTC)
    assert en_datetime(src) is src  # aware → renvoyée telle quelle, sans suppose


def test_en_datetime_mauvais_type():
    with pytest.raises(TypeError):
        en_datetime("2020-05-04")


def test_debut_de_jour_conserve_le_fuseau():
    dt = datetime(2020, 5, 4, 13, 37, 42, 5, tzinfo=UTC)
    assert debut_de_jour(dt) == datetime(2020, 5, 4, 0, 0, tzinfo=UTC)


def test_debut_de_semaine_lundi_par_defaut():
    mercredi = datetime(2020, 1, 1, 15, 0, tzinfo=UTC)  # 2020-01-01 = mercredi
    assert debut_de_semaine(mercredi) == datetime(2019, 12, 30, 0, 0, tzinfo=UTC)
    # premier_jour=6 → dimanche
    assert debut_de_semaine(mercredi, premier_jour=6) == datetime(
        2019, 12, 29, 0, 0, tzinfo=UTC
    )


def test_debut_de_mois():
    dt = datetime(2020, 5, 4, 13, 0, tzinfo=UTC)
    assert debut_de_mois(dt) == datetime(2020, 5, 1, 0, 0, tzinfo=UTC)


def test_arrondi_au_quart_d_heure():
    quart = timedelta(minutes=15)
    assert arrondi(datetime(2020, 1, 1, 10, 7, tzinfo=UTC), quart) == datetime(
        2020, 1, 1, 10, 0, tzinfo=UTC
    )
    assert arrondi(datetime(2020, 1, 1, 10, 8, tzinfo=UTC), quart) == datetime(
        2020, 1, 1, 10, 15, tzinfo=UTC
    )


def test_arrondi_pas_negatif_leve():
    with pytest.raises(ValueError):
        arrondi(datetime(2020, 1, 1, tzinfo=UTC), timedelta(0))


def test_intervalle():
    debut = datetime(2020, 1, 1, 0, 0, tzinfo=UTC)
    fin = datetime(2020, 1, 1, 1, 0, tzinfo=UTC)
    pas = timedelta(minutes=20)
    points = list(intervalle(debut, fin, pas))
    assert points == [
        datetime(2020, 1, 1, 0, 0, tzinfo=UTC),
        datetime(2020, 1, 1, 0, 20, tzinfo=UTC),
        datetime(2020, 1, 1, 0, 40, tzinfo=UTC),
    ]  # 1:00 exclu (strictement avant `fin`)


def test_intervalle_pas_negatif_leve():
    d = datetime(2020, 1, 1, tzinfo=UTC)
    with pytest.raises(ValueError):
        list(intervalle(d, d, timedelta(0)))
