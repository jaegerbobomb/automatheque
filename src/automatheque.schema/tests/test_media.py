# -*- coding: utf-8 -*-
"""Tests de `schema.media`."""

import attr
from automatheque.schema.media import Media


@attr.s
class Image(Media):
    """Une famille qui déclare ses extensions."""

    extensions = ("jpg", "png")


def test_extension_en_minuscules_sans_le_point():
    assert Media(source="/photos/vacances.JPG").extension == "jpg"


def test_extension_vide_si_le_fichier_n_en_a_pas():
    assert Media(source="/photos/LISEZMOI").extension == ""


def test_mimetype_devine_depuis_le_nom():
    assert Media(source="/photos/vacances.jpg").mimetype == "image/jpeg"


def test_mimetype_inconnu_renvoie_none():
    assert Media(source="/photos/vacances.inconnu").mimetype is None


def test_valide_selon_les_extensions_de_la_famille():
    assert Image(source="/photos/vacances.jpg").valide()
    assert Image(source="/photos/vacances.PNG").valide()
    assert not Image(source="/photos/vacances.gif").valide()


def test_media_nu_n_est_jamais_valide():
    """Sans famille, aucune extension n'est reconnue."""
    assert not Media(source="/photos/vacances.jpg").valide()


def test_empreinte_absente_par_defaut():
    """La calculer réclamerait de lire le fichier : ce n'est pas fait ici."""
    assert Media(source="/photos/vacances.jpg").empreinte is None


def test_empreinte_hors_du_constructeur():
    m = Media(source="/photos/vacances.jpg")
    m.empreinte = "abc123"
    assert m.empreinte == "abc123"
