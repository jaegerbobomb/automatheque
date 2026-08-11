# -*- coding: utf-8 -*-
"""Tests des durées humaines et de l'humanisation relative (`util.temps`, #132)."""

from datetime import datetime, timedelta, timezone

import pytest
from automatheque.exceptions import AutomathequeBaseException, DureeInvalide
from automatheque.util import (
    Vocabulaire,
    humanise_duree,
    humanise_relatif,
    parse_duree,
)

UTC = timezone.utc


# --- parse_duree ------------------------------------------------------------


@pytest.mark.parametrize(
    "chaine, secondes",
    [
        ("90s", 90),
        ("2m", 120),
        ("1h", 3600),
        ("2d", 2 * 86400),
        ("2j", 2 * 86400),
        ("1w", 604800),
        ("1sem", 604800),
        ("1h30", 3600 + 1800),  # nombre nu implicite → minutes
        ("1h 30m", 3600 + 1800),
        ("1j2h", 86400 + 7200),
        ("1m30", 90),  # nombre nu implicite → secondes
        ("  2H 15MIN  ", 2 * 3600 + 15 * 60),  # casse + espaces tolérés
        ("2 heures", 7200),  # unité en toutes lettres
        ("1 week 2 days", 604800 + 2 * 86400),  # anglais en entrée
    ],
)
def test_parse_duree_valide(chaine, secondes):
    assert parse_duree(chaine) == timedelta(seconds=secondes)


def test_m_vaut_une_minute_jamais_un_mois():
    assert parse_duree("1m") == timedelta(minutes=1)


@pytest.mark.parametrize("chaine", ["1mo", "1mois", "2 mois", "1month", "3 months"])
def test_mois_refuse_explicitement(chaine):
    with pytest.raises(DureeInvalide):
        parse_duree(chaine)


@pytest.mark.parametrize("chaine", ["", "   ", "abc", "90", "1z", "1h30x"])
def test_parse_duree_invalide_leve(chaine):
    with pytest.raises(DureeInvalide):
        parse_duree(chaine)


def test_duree_invalide_est_dans_la_hierarchie_et_valueerror():
    assert issubclass(DureeInvalide, AutomathequeBaseException)
    assert issubclass(DureeInvalide, ValueError)


def test_parse_duree_refuse_les_non_chaines():
    with pytest.raises(DureeInvalide):
        parse_duree(90)  # type: ignore[arg-type]


# --- humanise_duree ---------------------------------------------------------


def test_humanise_duree_zero():
    assert humanise_duree(timedelta(0)) == "0s"


def test_humanise_duree_decompose():
    assert humanise_duree(timedelta(days=1, hours=2, minutes=30, seconds=15)) == (
        "1j 2h 30m 15s"
    )


def test_humanise_duree_saute_les_composantes_nulles():
    assert humanise_duree(timedelta(hours=2, seconds=5)) == "2h 5s"


def test_humanise_duree_negative_leve():
    with pytest.raises(ValueError):
        humanise_duree(timedelta(seconds=-1))


def test_humanise_duree_arrondit_les_microsecondes():
    assert humanise_duree(timedelta(seconds=1, microseconds=600000)) == "2s"


@pytest.mark.parametrize(
    "duree",
    [
        timedelta(seconds=45),
        timedelta(minutes=5),
        timedelta(hours=1, minutes=30),
        timedelta(days=3),
        timedelta(weeks=2),
        timedelta(days=1, hours=2, minutes=3, seconds=4),
    ],
)
def test_aller_retour_parse_humanise(duree):
    # Le critère d'acceptation central : parse(humanise(d)) == d.
    assert parse_duree(humanise_duree(duree)) == duree


# --- humanise_relatif -------------------------------------------------------


def _ref():
    return datetime(2020, 1, 1, 12, 0, tzinfo=UTC)


def test_relatif_passe():
    instant = _ref() - timedelta(minutes=5)
    assert humanise_relatif(instant, maintenant=_ref()) == "il y a 5 min"


def test_relatif_futur():
    instant = _ref() + timedelta(days=2)
    assert humanise_relatif(instant, maintenant=_ref()) == "dans 2 j"


def test_relatif_a_l_instant():
    assert humanise_relatif(_ref(), maintenant=_ref()) == "à l'instant"


def test_relatif_grossier_arrondit_a_la_plus_grande_unite():
    instant = _ref() - timedelta(hours=1, minutes=30)
    assert humanise_relatif(instant, maintenant=_ref()) == "il y a 2 h"


def test_relatif_monte_jusqu_a_la_semaine():
    instant = _ref() - timedelta(weeks=3)
    assert humanise_relatif(instant, maintenant=_ref()) == "il y a 3 sem"


def test_relatif_recoit_son_maintenant_est_obligatoire():
    with pytest.raises(TypeError):
        humanise_relatif(_ref())  # type: ignore[call-arg]


def test_relatif_vocabulaire_personnalise():
    en = Vocabulaire(
        instant="just now",
        passe="{duree} ago",
        futur="in {duree}",
        unites=(("w", 604800), ("d", 86400), ("h", 3600), ("min", 60), ("s", 1)),
    )
    instant = _ref() - timedelta(days=2)
    assert humanise_relatif(instant, maintenant=_ref(), vocabulaire=en) == "2 d ago"


def test_relatif_seuil_instant_parametrable():
    instant = _ref() - timedelta(seconds=30)
    # Avec un seuil large, un écart de 30 s est considéré « à l'instant ».
    assert (
        humanise_relatif(instant, maintenant=_ref(), seuil_instant=timedelta(minutes=1))
        == "à l'instant"
    )


# --- parse_date_floue -------------------------------------------------------


def test_parse_date_floue_sans_extra_leve_import_nomme():
    try:
        import dateutil  # noqa: F401
    except ImportError:
        from automatheque.util import parse_date_floue

        with pytest.raises(ImportError, match=r"automatheque\[dates\]"):
            parse_date_floue("2020-01-01")
    else:
        pytest.skip("dateutil est installé : le chemin d'erreur n'est pas exerçable")
