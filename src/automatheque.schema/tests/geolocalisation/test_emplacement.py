# -*- coding: utf-8 -*-
"""Tests de `schema.geolocalisation`."""

import pytest
from automatheque.schema.geolocalisation import Emplacement


def test_coordonnees_converties_en_float():
    e = Emplacement("48.8584", "2.2945")
    assert e.latitude == pytest.approx(48.8584)
    assert e.longitude == pytest.approx(2.2945)


def test_valide_avec_des_coordonnees():
    assert Emplacement(48.8584, 2.2945).valide()


def test_valide_avec_une_adresse_seule():
    assert Emplacement(adresse="5 avenue Anatole France, Paris").valide()


def test_invalide_si_vide():
    assert not Emplacement().valide()


def test_invalide_si_une_seule_coordonnee():
    assert not Emplacement(latitude=48.8584).valide()


def test_decimal_en_dms():
    """Régression : les divmod avaient disparu, la fonction ne tournait pas."""
    degres, minutes, secondes, signe = Emplacement.decimal_en_dms(-38.2410611)
    assert (degres, signe) == (38.0, -1)
    assert minutes == 14.0
    assert secondes == pytest.approx(27.82, abs=0.01)


def test_decimal_en_dms_positif():
    assert Emplacement.decimal_en_dms(48.5)[3] == 1


def test_dms_en_decimal():
    assert Emplacement.dms_en_decimal(38, 14, 27.82, "S") == pytest.approx(
        -38.2410611, abs=1e-6
    )
    assert Emplacement.dms_en_decimal(38, 14, 27.82, "N") == pytest.approx(
        38.2410611, abs=1e-6
    )


def test_dms_en_decimal_sans_direction():
    assert Emplacement.dms_en_decimal(10, 30, 0) == pytest.approx(10.5)


def test_aller_retour_dms():
    degres, minutes, secondes, _ = Emplacement.decimal_en_dms(48.8584)
    assert Emplacement.dms_en_decimal(degres, minutes, secondes) == pytest.approx(
        48.8584, abs=1e-9
    )


def test_dms_en_chaine():
    assert Emplacement.dms_en_chaine(-38.5, "latitude").endswith(" S")
    assert Emplacement.dms_en_chaine(38.5, "latitude").endswith(" N")
    assert Emplacement.dms_en_chaine(-2.5, "longitude").endswith(" W")
    assert Emplacement.dms_en_chaine(2.5, "longitude").endswith(" E")


def test_dms_en_chaine_produit_le_format_exiftool_exact():
    """#116-4 : degrés/minutes entiers, secondes arrondies — avant on obtenait
    « 38.0 deg 14.0' 27.8199…" »."""
    assert Emplacement.dms_en_chaine(-38.2410611, "latitude") == "38 deg 14' 27.82\" S"


def test_dms_en_chaine_refuse_un_axe_inconnu():
    with pytest.raises(ValueError):
        Emplacement.dms_en_chaine(2.5, "altitude")


def test_distance_est_nulle_pour_le_meme_point():
    e = Emplacement(48.8584, 2.2945)
    assert e.distance(48.8584, 2.2945) == pytest.approx(0)


def test_distance_approximative_entre_deux_points_proches():
    """Tour Eiffel → Arc de Triomphe : environ 1,7 km à vol d'oiseau."""
    eiffel = Emplacement(48.8584, 2.2945)
    assert eiffel.distance(48.8738, 2.2950) == pytest.approx(1700, abs=100)


def test_distance_croit_avec_l_ecart():
    eiffel = Emplacement(48.8584, 2.2945)
    assert eiffel.distance(48.8738, 2.2950) < eiffel.distance(48.9, 2.2950)


def test_valide_sur_l_equateur():
    """Régression : `if latitude and longitude` — zéro est falsy."""
    assert Emplacement(0.0, 9.45).valide()


def test_valide_sur_le_meridien_de_greenwich():
    assert Emplacement(51.48, 0.0).valide()


def test_valide_a_l_intersection_des_deux():
    assert Emplacement(0.0, 0.0).valide()


def test_coordonnees_absentes_par_defaut():
    """`None` et non `0` : « pas de coordonnée » se distingue de « zéro »."""
    e = Emplacement()
    assert e.latitude is None and e.longitude is None
    assert not e.valide()


def test_une_seule_coordonnee_ne_suffit_pas():
    assert not Emplacement(latitude=48.8584).valide()
    assert not Emplacement(longitude=2.2945).valide()


def test_distance_sans_coordonnees_leve_une_erreur_claire():
    with pytest.raises(ValueError, match="sans coordonnées"):
        Emplacement(adresse="quelque part").distance(48.8584, 2.2945)


def test_distance_depuis_l_equateur():
    """Le point de départ est valide : la distance doit se calculer."""
    assert Emplacement(0.0, 0.0).distance(0.0, 0.0) == pytest.approx(0)
