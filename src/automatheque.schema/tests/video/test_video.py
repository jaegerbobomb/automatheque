# -*- coding: utf-8 -*-
"""Tests de `schema.video`."""

from datetime import date

import pytest
from automatheque.schema.media import Media
from automatheque.schema.video import Episode, Film, Serie, Video


@pytest.mark.parametrize("classe", [Video, Episode, Film])
def test_les_videos_sont_des_media(classe):
    assert isinstance(classe(source="/videos/a.mkv"), Media)


@pytest.mark.parametrize("classe", [Episode, Film])
def test_valide_selon_l_extension_sans_ouvrir_le_fichier(classe):
    assert classe(source="/nexiste/pas/du/tout.MKV").valide()
    assert classe(source="/videos/b.mp4").valide()
    assert not classe(source="/videos/notes.txt").valide()


def test_basename():
    assert Film(source="/videos/films/a.mkv").basename == "a.mkv"
    assert Film().basename is None


def test_episode_par_defaut():
    episode = Episode(source="/videos/a.mkv")
    assert episode.serie == Serie()
    assert episode.saison is None
    assert episode.numeros == ()
    assert episode.titre is None
    assert episode.ids == {}


def test_serie_par_defaut_propre_a_chaque_episode():
    a, b = Episode(), Episode()
    a.serie.titre = "A"
    assert b.serie.titre is None


def test_numeros_tries_et_dedoublonnes():
    """Un fichier peut contenir plusieurs épisodes : les numéros forment un
    ensemble, rendu trié pour être comparable et gabaritable."""
    assert Episode(numeros={2, 1, 2}).numeros == (1, 2)
    assert Episode(numeros=[3]).numeros == (3,)


def test_numeros_entiers():
    assert Episode(numeros=["4", 5]).numeros == (4, 5)


def test_episode_complet():
    episode = Episode(
        source="/videos/a.mkv",
        serie=Serie(titre="Une Serie", annee=2005, ids={"tvdb": 12}),
        saison=1,
        numeros={1},
        titre="Le Pilote",
        date_diffusion=date(2005, 3, 26),
        ids={"imdb": "tt0000001", "tmdb": 42},
    )
    assert episode.serie.titre == "Une Serie"
    assert episode.serie.ids == {"tvdb": "12"}
    assert episode.saison == 1
    assert episode.date_diffusion == date(2005, 3, 26)


def test_ids_normalises_en_chaines():
    """Un id externe circule tel qu'un service l'écrit : on ne mélange pas
    `42` et `"42"` selon l'adaptateur qui l'a rempli."""
    assert Film(ids={"tmdb": 42, "imdb": "tt1"}).ids == {"tmdb": "42", "imdb": "tt1"}


def test_film():
    film = Film(source="/videos/a.mkv", titre="Un Film", annee=2010)
    assert (film.titre, film.annee) == ("Un Film", 2010)


def test_film_par_defaut():
    film = Film()
    assert (film.titre, film.annee, film.ids) == (None, None, {})


def test_champs_nommes_uniquement():
    """Au-delà de `source`, tout se passe par nom : l'ordre des champs n'est
    pas une API."""
    with pytest.raises(TypeError):
        Film("/videos/a.mkv", "Un Film")  # type: ignore[misc]


def test_aucune_normalisation_du_titre():
    """Le vocabulaire range ce qu'on lui donne : nettoyer un nom de fichier est
    l'affaire de l'application (décomposition, gabarits)."""
    assert Serie(titre="[team] mr.robot").titre == "[team] mr.robot"
    assert Film(titre="the.matrix").titre == "the.matrix"
