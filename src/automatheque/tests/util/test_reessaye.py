# -*- coding: utf-8 -*-
"""Tests du décorateur de réessais (util/reessaye.py)."""

from unittest.mock import Mock, call, patch

import pytest
from automatheque.util.reessaye import reessaye


def test_reussite_premier_essai_sans_attente():
    """Si la fonction réussit du premier coup, aucune attente n'a lieu."""
    fonction = Mock(return_value="ok")
    decoree = reessaye()(fonction)

    with patch("automatheque.util.reessaye.sleep") as sleep:
        assert decoree("a", b=2) == "ok"

    fonction.assert_called_once_with("a", b=2)
    sleep.assert_not_called()


def test_reessaie_puis_reussit_avec_delais_croissants():
    """Échoue 2 fois puis réussit : 3 appels, pauses 2s puis 4s (multiplicateur=2)."""
    fonction = Mock(side_effect=[ConnectionError(), ConnectionError(), "ok"])
    decoree = reessaye(
        tentatives=4, delai=2, multiplicateur=2, exceptions=(ConnectionError,)
    )(fonction)

    with patch("automatheque.util.reessaye.sleep") as sleep:
        assert decoree() == "ok"

    assert fonction.call_count == 3
    assert sleep.call_args_list == [call(2), call(4)]


def test_epuise_les_tentatives_et_releve_la_derniere_exception():
    """Si tous les essais échouent, la dernière exception est relevée."""
    derniere = ValueError("boom-3")
    fonction = Mock(side_effect=[ValueError("boom-1"), ValueError("boom-2"), derniere])
    decoree = reessaye(tentatives=3, delai=1, exceptions=(ValueError,))(fonction)

    with patch("automatheque.util.reessaye.sleep") as sleep:
        with pytest.raises(ValueError) as info:
            decoree()

    assert info.value is derniere
    assert fonction.call_count == 3
    # 3 tentatives => 2 attentes entre les essais.
    assert sleep.call_count == 2


def test_exception_non_ciblee_se_propage_sans_reessai():
    """Une exception hors de la liste ciblée n'est pas réessayée."""
    fonction = Mock(side_effect=KeyError("absente"))
    decoree = reessaye(tentatives=5, exceptions=(ValueError,))(fonction)

    with patch("automatheque.util.reessaye.sleep") as sleep:
        with pytest.raises(KeyError):
            decoree()

    fonction.assert_called_once()
    sleep.assert_not_called()


def test_accepte_une_exception_unique_hors_tuple():
    """`exceptions` peut être une classe seule (pas forcément un tuple)."""
    fonction = Mock(side_effect=[TimeoutError(), "ok"])
    decoree = reessaye(tentatives=2, delai=1, exceptions=TimeoutError)(fonction)

    with patch("automatheque.util.reessaye.sleep"):
        assert decoree() == "ok"

    assert fonction.call_count == 2


def test_gigue_ajoute_au_delai():
    """La gigue ajoute une part aléatoire bornée au délai de base."""
    fonction = Mock(side_effect=[ConnectionError(), "ok"])
    decoree = reessaye(tentatives=2, delai=3, gigue=1, exceptions=(ConnectionError,))(
        fonction
    )

    cible = "automatheque.util.reessaye.uniform"
    with patch(cible, return_value=0.5) as uniform:
        with patch("automatheque.util.reessaye.sleep") as sleep:
            assert decoree() == "ok"

    uniform.assert_called_once_with(0, 1)
    sleep.assert_called_once_with(3.5)


def test_tentatives_invalides_leve_valueerror():
    """Une configuration aberrante est rejetée à la décoration."""
    with pytest.raises(ValueError):
        reessaye(tentatives=0)

    with pytest.raises(ValueError):
        reessaye(delai=-1)


def test_preserve_les_metadonnees_de_la_fonction():
    """functools.wraps : nom et docstring de la fonction d'origine conservés."""

    @reessaye()
    def appel_api():
        """Docstring d'origine."""
        return 42

    assert appel_api.__name__ == "appel_api"
    assert appel_api.__doc__ == "Docstring d'origine."
    assert appel_api() == 42
