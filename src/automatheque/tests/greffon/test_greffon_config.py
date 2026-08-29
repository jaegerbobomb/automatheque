# -*- coding: utf-8 -*-
"""Un greffon qui exige une configuration voit celle-ci réellement vérifiée (#139).

Avant, `config_requise` + `actif` ne répondaient qu'à « une configuration
existe-t-elle ? » — jamais « la mienne est-elle là, et bien typée ? ». Un greffon
mal configuré se déclarait donc actif, et l'erreur ressortait plus tard, au point
d'usage.
"""

from configparser import ConfigParser

import attr
import pytest
from automatheque.configuration import booleen
from automatheque.exceptions import ConfigurationInvalide
from automatheque.greffon import Greffon


@attr.s
class ConfigMeteo:
    """Section attendue par le greffon météo."""

    cle_api = attr.ib(validator=attr.validators.instance_of(str))
    hote = attr.ib(default="api.exemple.org", converter=str)
    actif = attr.ib(default=True, converter=booleen)


@attr.s(eq=False)
class GreffonMeteo(Greffon):
    CONFIG = ConfigMeteo
    SECTION_CONFIG = "meteo"


@attr.s(eq=False)
class GreffonSansConfig(Greffon):
    """Greffon historique : aucune `CONFIG` déclarée."""


def _config(texte):
    config = ConfigParser()
    config.read_string(texte)
    return config


def _greffon(classe, texte):
    """Instancie `classe` en lui posant la configuration `texte`.

    `config` est `init=False` (rempli par `charge_configuration`) : on la
    remplace après coup, ce qui évite de toucher à la configuration réelle.
    """
    greffon = classe()
    greffon.config = _config(texte)
    return greffon


# --- Section valide ---------------------------------------------------------


def test_section_valide_rend_le_greffon_actif():
    greffon = _greffon(GreffonMeteo, "[meteo]\ncle_api = abc\n")
    assert greffon.actif is True


def test_reglages_sont_types_et_memoises():
    greffon = _greffon(
        GreffonMeteo, "[meteo]\ncle_api = abc\nhote = m.example\nactif = no\n"
    )
    reglages = greffon.reglages
    assert reglages.cle_api == "abc"
    assert reglages.hote == "m.example"
    assert reglages.actif is False  # converti, pas la chaîne "no"
    # Mémoïsé : le même objet est renvoyé sans revalider.
    assert greffon.reglages is reglages


# --- Section absente / invalide ---------------------------------------------


def test_section_absente_rend_le_greffon_inactif(caplog):
    greffon = _greffon(GreffonMeteo, "[autre]\nx = 1\n")
    assert greffon.actif is False
    assert "inactif" in caplog.text


def test_cle_requise_manquante_rend_inactif():
    greffon = _greffon(GreffonMeteo, "[meteo]\nhote = m.example\n")
    assert greffon.actif is False


def test_valeur_invalide_rend_inactif():
    greffon = _greffon(GreffonMeteo, "[meteo]\ncle_api = abc\nactif = peut-etre\n")
    assert greffon.actif is False


def test_actif_ne_leve_jamais():
    """`actif` est un état, pas une opération : il journalise et renvoie False."""
    greffon = _greffon(GreffonMeteo, "")
    assert greffon.actif is False


def test_valide_config_leve_avec_le_detail():
    greffon = _greffon(GreffonMeteo, "[meteo]\nhote = m.example\n")
    with pytest.raises(ConfigurationInvalide) as info:
        greffon.valide_config()
    # L'erreur nomme la section et la clé fautive.
    assert "meteo" in str(info.value)
    assert "cle_api" in str(info.value)


def test_reglages_leve_aussi():
    greffon = _greffon(GreffonMeteo, "[meteo]\nhote = m.example\n")
    with pytest.raises(ConfigurationInvalide):
        greffon.reglages


# --- Rétro-compatibilité ----------------------------------------------------


def test_sans_config_comportement_historique():
    greffon = _greffon(GreffonSansConfig, "[quoi]\nque = ce soit\n")
    assert greffon.CONFIG is None
    assert greffon.reglages is None
    assert greffon.valide_config() is None
    # `config_requise` est faux par défaut → actif, comme avant.
    assert greffon.actif is True


def test_sans_config_mais_config_requise():
    greffon = _greffon(GreffonSansConfig, "[quoi]\nque = ce soit\n")
    greffon.config_requise = True
    # Comportement historique conservé : une configuration existe → actif.
    assert greffon.actif is True


def test_section_par_defaut_est_la_cle_du_greffon():
    """Sans `SECTION_CONFIG`, la section lue est la `cle` du greffon."""

    @attr.s(eq=False)
    class GreffonKodi(Greffon):
        CONFIG = ConfigMeteo

    greffon = _greffon(GreffonKodi, "[kodi]\ncle_api = xyz\n")
    assert greffon.section_config == "kodi"
    assert greffon.actif is True
    assert greffon.reglages.cle_api == "xyz"
