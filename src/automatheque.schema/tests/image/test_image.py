# -*- coding: utf-8 -*-
"""Tests de `schema.image`."""

from datetime import datetime, timezone

import attr
from automatheque.schema.image import BaseTags, Photo
from automatheque.schema.media import Media


def test_photo_est_un_media():
    assert isinstance(Photo(source="/photos/vacances.jpg"), Media)


def test_photo_valide_selon_son_extension():
    assert Photo(source="/photos/vacances.JPG").valide()
    assert Photo(source="/photos/brut.cr2").valide()
    assert not Photo(source="/photos/notes.txt").valide()


def test_photo_valide_sans_ouvrir_le_fichier():
    """Aucun accès disque : le fichier n'a pas besoin d'exister."""
    assert Photo(source="/nexiste/pas/du/tout.jpg").valide()


def test_basename():
    assert Photo(source="/photos/2019/vacances.jpg").basename == "vacances.jpg"


def test_basename_sans_source():
    assert Photo().basename is None


def test_tags_par_defaut_rattaches_a_la_source():
    photo = Photo(source="/photos/vacances.jpg")
    assert isinstance(photo.tags, BaseTags)
    assert photo.tags.source == "/photos/vacances.jpg"


def test_tags_par_defaut_propres_a_chaque_photo():
    """La fabrique est rejouée à chaque instanciation, pas partagée."""
    a, b = Photo(source="/a.jpg"), Photo(source="/b.jpg")
    a.tags.album = "A"
    assert b.tags.album is None


def test_tags_fournis_a_la_construction():
    tags = BaseTags(source="/photos/vacances.jpg", album="Vacances")
    assert Photo("/photos/vacances.jpg", tags).tags.album == "Vacances"


def test_tags_vides_par_defaut():
    tags = BaseTags()
    for attribut in BaseTags.ATTRIBUTS_CHARGES:
        assert getattr(tags, attribut) is None


def test_tags_acceptent_le_vocabulaire_complet():
    tags = BaseTags(
        source="/photos/vacances.jpg",
        album="Japon",
        auteur="Photographe",
        titre="Osaka de nuit",
        description="Vue depuis l'hôtel",
        evaluation=5,
        nom_origine="DSC_0001.jpg",
        date_prise_de_vue=datetime(2013, 3, 17, 1, 0, tzinfo=timezone.utc),
        timezone="Asia/Tokyo",
        latitude=34.6937,
        longitude=135.5023,
        ville="Osaka",
        pays="JP",
    )
    assert tags.album == "Japon"
    assert tags.latitude == 34.6937
    assert tags.timezone == "Asia/Tokyo"


def test_charge_sans_adaptateur_ne_fait_rien():
    tags = BaseTags(source="/photos/vacances.jpg")
    assert tags.charge() is tags
    assert tags.album is None


def test_un_adaptateur_surcharge_charge():
    """Le scénario visé : l'adaptateur d'I/O est une sous-classe, pas la base."""

    @attr.s
    class TagsFigees(BaseTags):
        def charge(self):
            self.album = "Depuis l'adaptateur"
            return self

    photo = Photo(source="/photos/vacances.jpg")
    photo.tags = TagsFigees(source=photo.source)
    assert photo.charge_tags().album == "Depuis l'adaptateur"


def test_repr_montre_les_etiquettes():
    """Régression : le motif attr.ib + property masquait les valeurs."""
    assert "album='Japon'" in repr(BaseTags(album="Japon"))
