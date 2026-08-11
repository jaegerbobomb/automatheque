# -*- coding: utf-8 -*-
"""Tests de `schema.calendrier`."""

from datetime import date, datetime, timezone

import pytest
from automatheque.schema.calendrier import Evenement

vobject = pytest.importorskip("vobject")


VEVENT = """BEGIN:VEVENT
UID:1234@exemple.org
SUMMARY:Voyage au Japon
LOCATION:Osaka
DESCRIPTION:Deux semaines
DTSTART:20130317T010000Z
DTEND:20130331T040000Z
END:VEVENT
"""

VEVENT_JOURNEE_ENTIERE = """BEGIN:VEVENT
UID:5678@exemple.org
SUMMARY:JRPASS
DTSTART;VALUE=DATE:20150509
DTEND;VALUE=DATE:20150516
END:VEVENT
"""


def test_structure_pure_sans_vevent():
    """`Evenement` s'utilise sans jamais toucher à iCalendar."""
    ev = Evenement(titre="Anniversaire", date_debut=datetime(2024, 5, 1, 12, 0))
    assert ev.titre == "Anniversaire"
    assert ev.date_fin is None


def test_dates_naives_deviennent_tz_aware():
    ev = Evenement(date_debut=datetime(2024, 5, 1, 12, 0))
    assert ev.date_debut.tzinfo is not None
    assert ev.date_debut.utcoffset().total_seconds() == 0


def test_date_nue_devient_datetime_a_minuit():
    ev = Evenement(date_debut=date(2024, 5, 1))
    assert ev.date_debut == datetime(2024, 5, 1, 0, 0, tzinfo=timezone.utc)


def test_date_deja_tz_aware_est_conservee():
    attendu = datetime(2024, 5, 1, 12, 0, tzinfo=timezone.utc)
    assert Evenement(date_debut=attendu).date_debut == attendu


def test_depuis_vevent_serialise():
    ev = Evenement.depuis_vevent(VEVENT, etag="etag-1", url="https://exemple/1")
    assert ev.titre == "Voyage au Japon"
    assert ev.lieu == "Osaka"
    assert ev.description == "Deux semaines"
    assert ev.uid == "1234@exemple.org"
    assert ev.etag == "etag-1"
    assert ev.url == "https://exemple/1"
    assert ev.date_debut == datetime(2013, 3, 17, 1, 0, tzinfo=timezone.utc)
    assert ev.date_fin == datetime(2013, 3, 31, 4, 0, tzinfo=timezone.utc)


def test_depuis_vevent_instance_vobject():
    ev = Evenement.depuis_vevent(vobject.readOne(VEVENT))
    assert ev.titre == "Voyage au Japon"


def test_depuis_vevent_journee_entiere():
    """Un DTSTART de type DATE devient une datetime à minuit UTC."""
    ev = Evenement.depuis_vevent(VEVENT_JOURNEE_ENTIERE)
    assert ev.date_debut == datetime(2015, 5, 9, 0, 0, tzinfo=timezone.utc)
    assert ev.lieu is None


def test_depuis_vevent_sans_duree_ni_fin():
    sans_fin = VEVENT.replace("DTEND:20130331T040000Z\n", "")
    assert Evenement.depuis_vevent(sans_fin).date_fin is None


def test_depuis_vevent_avec_duration_non_gere():
    avec_duree = VEVENT.replace("DTEND:20130331T040000Z", "DURATION:PT1H")
    with pytest.raises(NotImplementedError):
        Evenement.depuis_vevent(avec_duree)


def test_vers_vevent():
    ev = Evenement(
        titre="Voyage au Japon",
        lieu="Osaka",
        uid="1234@exemple.org",
        date_debut=datetime(2013, 3, 17, 1, 0, tzinfo=timezone.utc),
        date_fin=datetime(2013, 3, 31, 4, 0, tzinfo=timezone.utc),
    )
    vevent = ev.vers_vevent()
    assert vevent.summary.value == "Voyage au Japon"
    assert vevent.location.value == "Osaka"
    assert vevent.dtstart.value == ev.date_debut
    assert "Voyage au Japon" in vevent.serialize()


def test_vers_vevent_depuis_une_date_naive_serialise_en_z():
    """#48 : une date naïve devient tz-aware avec un UTC **nommé**
    (`ZoneInfo("UTC")`), que vobject sérialise directement en `Z` — sans passer
    par le contournement `_pour_vobject` (réservé aux décalages fixes anonymes
    comme `datetime.timezone.utc`)."""
    ev = Evenement(
        uid="x@exemple.org", titre="T", date_debut=datetime(2013, 3, 17, 1, 0)
    )
    assert "DTSTART:20130317T010000Z" in ev.vers_vevent().serialize()


def test_vers_vevent_n_ecrit_pas_les_champs_vides():
    vevent = Evenement(titre="Sans lieu").vers_vevent()
    assert not hasattr(vevent, "location")


def test_aller_retour_vevent():
    ev = Evenement.depuis_vevent(VEVENT)
    retour = Evenement.depuis_vevent(ev.vers_vevent())
    assert retour == Evenement(
        titre=ev.titre,
        lieu=ev.lieu,
        description=ev.description,
        uid=ev.uid,
        date_debut=ev.date_debut,
        date_fin=ev.date_fin,
    )


def test_date_fin_abregee_ne_garde_que_ce_qui_change():
    ev = Evenement(date_debut=date(2018, 3, 14), date_fin=date(2018, 4, 12))
    assert ev.date_fin_abregee == [4, 12]


def test_date_fin_abregee_avec_changement_d_annee():
    ev = Evenement(date_debut=date(2018, 12, 30), date_fin=date(2019, 1, 2))
    assert ev.date_fin_abregee == [2019, 1, 2]


def test_date_fin_abregee_vide_le_meme_jour():
    ev = Evenement(
        date_debut=datetime(2018, 3, 14, 9, 0), date_fin=datetime(2018, 3, 14, 18, 0)
    )
    assert ev.date_fin_abregee == []


def test_date_fin_abregee_vide_sans_date_de_fin():
    assert Evenement(date_debut=date(2018, 3, 14)).date_fin_abregee == []
