# -*- coding: utf-8 -*-
"""Tests du value object Montant : exactitude Decimal, devises, parsing, locale."""

from decimal import Decimal

import pytest
from automatheque.schema.monnaie import (
    FR,
    US,
    DevisesIncompatibles,
    Montant,
    MontantInvalide,
)


@pytest.mark.parametrize(
    ("texte", "attendu"),
    [
        ("10,5", Decimal("10.5")),
        ("10,500.00", Decimal("10500.00")),
        ("10 500,00", Decimal("10500.00")),
        ("1 234,56 €", Decimal("1234.56")),  # espaces insécables + symbole
        ("-45.60", Decimal("-45.60")),
        ("+3", Decimal("3")),
        ("10.50 USD", Decimal("10.50")),  # code devise en lettres ignoré
    ],
)
def test_depuis_texte_heuristique(texte, attendu):
    assert Montant.depuis_texte(texte).valeur == attendu


def test_depuis_texte_format_explicite_leve_l_ambiguite():
    # "1,234" est ambigu : le format tranche.
    assert Montant.depuis_texte("1,234", fmt=US).valeur == Decimal("1234")
    assert Montant.depuis_texte("1,234", fmt=FR).valeur == Decimal("1.234")
    assert Montant.depuis_texte("$1,234.56", fmt=US).valeur == Decimal("1234.56")


def test_exactitude_decimal():
    # le piège float classique : 0.1 + 0.2 != 0.3
    total = Montant.depuis_texte("0,1") + Montant.depuis_texte("0,2")
    assert total == Montant(Decimal("0.3"))


def test_float_refuse():
    with pytest.raises(MontantInvalide):
        Montant(0.1)
    with pytest.raises(MontantInvalide):
        Montant(Decimal("2")) * 1.5


def test_texte_illisible_refuse():
    with pytest.raises(MontantInvalide):
        Montant.depuis_texte("abc")


def test_devise_vide_refusee():
    with pytest.raises(MontantInvalide):
        Montant(Decimal("1"), devise="")


def test_devises_incompatibles():
    euros = Montant(Decimal("1"))
    dollars = Montant(Decimal("1"), devise="usd")  # normalisée en USD
    assert dollars.devise == "USD"
    with pytest.raises(DevisesIncompatibles):
        euros + dollars
    with pytest.raises(DevisesIncompatibles):
        euros < dollars
    # `==` inter-devises ne lève pas : deux devises ne sont pas « égales ».
    assert euros != dollars


def test_arithmetique_et_comparaisons():
    a = Montant.depuis_texte("10,00")
    b = Montant.depuis_texte("2,50")
    assert (a - b).valeur == Decimal("7.50")
    assert (-b).valeur == Decimal("-2.50")
    assert (3 * b).valeur == Decimal("7.50")
    assert (b * Decimal("2")).valeur == Decimal("5.00")
    assert b < a <= a and a > b >= b


def test_convertit_recoit_son_taux():
    montant = Montant.depuis_texte("10,00")  # 10 EUR
    usd = montant.convertit("USD", Decimal("1.08"))
    assert usd.devise == "USD"
    assert usd.valeur == Decimal("10.8000")
    with pytest.raises(MontantInvalide):  # taux float refusé
        montant.convertit("USD", 1.08)


def test_arrondi_au_centime():
    montant = Montant(Decimal("10.8049"))
    assert montant.arrondi().valeur == Decimal("10.80")
    assert Montant(Decimal("2.005")).arrondi(2).valeur == Decimal("2.01")  # half up


def test_formatage_francais():
    montant = Montant.depuis_texte("-1234567,8")
    assert str(montant) == "-1234567.8 EUR"
    # FR : milliers en espace fine insécable (U+202F), insécable (U+00A0) avant €
    assert montant.texte() == "-1 234 567,80 €"


def test_formatage_americain():
    montant = Montant(Decimal("1234.56"))
    # US : symbole avant, sans espace, virgule de milliers, point décimal
    assert montant.texte(fmt=US) == "$1,234.56"
