# -*- coding: utf-8 -*-
"""Tests du contrat `Langue` et du registre par points d'entrée (#136)."""

from datetime import datetime, timedelta, timezone

import pytest
from automatheque.exceptions import AutomathequeBaseException, LangueInconnue
from automatheque.util import (
    EN,
    FR,
    Langue,
    Vocabulaire,
    humanise_duree,
    humanise_relatif,
    langues_disponibles,
    parse_duree,
    resout_langue,
)
from automatheque.util import langues as mod_langues

UTC = timezone.utc


# --- Découverte du cœur *par* les points d'entrée ---------------------------


def test_fr_et_en_sont_decouverts_via_points_entree():
    # Le cœur ne se résout pas par un chemin privilégié : `fr`/`en` sont dans le
    # registre parce qu'ils sont déclarés en points d'entrée (comme un tiers).
    dispo = langues_disponibles()
    assert "fr" in dispo
    assert "en" in dispo


def test_code_resout_l_objet_du_coeur():
    # …et c'est bien le *même* objet (l'entry point charge l'attribut du module).
    assert resout_langue("fr") is FR
    assert resout_langue("en") is EN


def test_objet_langue_passe_tel_quel():
    assert resout_langue(FR) is FR


# --- Erreurs de résolution --------------------------------------------------


def test_langue_inconnue_leve_exception_nommee():
    with pytest.raises(LangueInconnue) as exc:
        resout_langue("xx")
    # Jamais un None ni un KeyError nu : une exception nommée de la hiérarchie…
    assert isinstance(exc.value, AutomathequeBaseException)
    assert isinstance(exc.value, LookupError)
    # …dont le message nomme quoi installer et liste le disponible.
    assert "automatheque.langues" in str(exc.value)
    assert exc.value.code == "xx"


def test_resout_langue_mauvais_type():
    with pytest.raises(TypeError):
        resout_langue(123)  # type: ignore[arg-type]


# --- Découverte d'une langue *tierce* (point d'entrée simulé) ----------------


class _FauxPoint:
    """Imite un `importlib.metadata.EntryPoint` : un `name` et un `load()`."""

    def __init__(self, name, objet):
        self.name = name
        self._objet = objet

    def load(self):
        return self._objet


# Une langue « tierce » : l'allemand, avec ses propres alias, mois refusés,
# libellés de sortie et vocabulaire relatif.
DE = Langue(
    code="de",
    alias={
        "s": "s",
        "sek": "s",
        "sekunde": "s",
        "sekunden": "s",
        "m": "m",
        "min": "m",
        "minute": "m",
        "minuten": "m",
        "h": "h",
        "std": "h",
        "stunde": "h",
        "stunden": "h",
        "t": "d",
        "tag": "d",
        "tage": "d",
        "w": "w",
        "woche": "w",
        "wochen": "w",
    },
    mois=frozenset({"monat", "monate", "mo"}),
    libelles_duree={"d": "t", "h": "h", "m": "m", "s": "s"},
    relatif=Vocabulaire(
        instant="gerade eben",
        passe="vor {duree}",
        futur="in {duree}",
        unites=(("w", 604800), ("t", 86400), ("h", 3600), ("min", 60), ("s", 1)),
    ),
)


@pytest.fixture
def avec_langue_de(monkeypatch):
    """Injecte `de` comme si un paquet tiers l'avait déclarée en point d'entrée."""

    def faux_entry_points(group=None):
        if group == mod_langues.GROUPE_LANGUES:
            return [
                _FauxPoint("fr", FR),
                _FauxPoint("en", EN),
                _FauxPoint("de", DE),
            ]
        return []

    monkeypatch.setattr(mod_langues, "entry_points", faux_entry_points)
    mod_langues._registre.cache_clear()  # oublie le registre déjà mémoïsé
    yield
    mod_langues._registre.cache_clear()  # et le restaure pour les autres tests


def test_langue_tierce_est_decouverte(avec_langue_de):
    assert "de" in langues_disponibles()
    assert resout_langue("de") is DE


def test_parse_avec_langue_tierce(avec_langue_de):
    assert parse_duree("2wochen", langue="de") == timedelta(weeks=2)
    assert parse_duree("1t 2h", langue="de") == timedelta(days=1, hours=2)


def test_humanise_avec_langue_tierce(avec_langue_de):
    assert humanise_duree(timedelta(days=1, hours=2), langue="de") == "1t 2h"


def test_mois_refuse_selon_la_langue_tierce(avec_langue_de):
    from automatheque.exceptions import DureeInvalide

    with pytest.raises(DureeInvalide):
        parse_duree("1monat", langue="de")


# --- `langue=` de bout en bout (cœur) ---------------------------------------


def test_humanise_duree_en_anglais():
    assert humanise_duree(timedelta(days=1, hours=2, minutes=30), langue="en") == (
        "1d 2h 30m"
    )


def test_humanise_relatif_en_anglais():
    m = datetime(2020, 1, 1, 12, 0, tzinfo=UTC)
    passe = datetime(2020, 1, 1, 11, 55, tzinfo=UTC)
    assert humanise_relatif(passe, maintenant=m, langue="en") == "5 min ago"


def test_parse_et_humanise_acceptent_un_objet_langue():
    assert parse_duree("1t", langue=DE) == timedelta(days=1)
    assert humanise_duree(timedelta(days=1), langue=DE) == "1t"


def test_aller_retour_par_langue():
    d = timedelta(days=1, hours=2, minutes=3, seconds=4)
    assert parse_duree(humanise_duree(d, langue="en"), langue="en") == d
    assert parse_duree(humanise_duree(d, langue=DE), langue=DE) == d


# --- Rétro-compat #132 : `vocabulaire=` -------------------------------------


def test_vocabulaire_explicite_l_emporte_sur_langue():
    m = datetime(2020, 1, 1, 12, 0, tzinfo=UTC)
    passe = datetime(2020, 1, 1, 11, 55, tzinfo=UTC)
    perso = Vocabulaire(passe="-{duree}")
    assert humanise_relatif(passe, maintenant=m, vocabulaire=perso) == "-5 min"


def test_une_langue_passee_comme_vocabulaire_utilise_son_relatif():
    m = datetime(2020, 1, 1, 12, 0, tzinfo=UTC)
    passe = datetime(2020, 1, 1, 11, 55, tzinfo=UTC)
    # Tolérance : une Langue passée à `vocabulaire=` → on prend son `relatif`.
    assert humanise_relatif(passe, maintenant=m, vocabulaire=EN) == "5 min ago"


def test_vocabulaire_mauvais_type():
    m = datetime(2020, 1, 1, 12, 0, tzinfo=UTC)
    with pytest.raises(TypeError):
        humanise_relatif(m, maintenant=m, vocabulaire="fr")  # type: ignore[arg-type]
