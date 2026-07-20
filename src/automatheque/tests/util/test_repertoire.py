# -*- coding: utf-8 -*-
"""Tests des utilitaires de manipulation des répertoires (util/repertoire.py)."""

from pathlib import Path

import pytest
from automatheque.util.repertoire import (
    iter_fichiers,
    mkdir_p,
    remonte_arborescence,
    supprime,
)


def test_mkdir_p_cree_arborescence(tmp_path):
    """mkdir_p crée toute l'arborescence manquante."""
    cible = tmp_path / "a" / "b" / "c"
    mkdir_p(str(cible))
    assert cible.is_dir()


def test_mkdir_p_idempotent_sur_repertoire_existant(tmp_path):
    """Recréer un répertoire existant ne lève pas d'erreur."""
    cible = tmp_path / "deja"
    cible.mkdir()
    mkdir_p(str(cible))  # ne doit pas lever
    assert cible.is_dir()


def test_mkdir_p_leve_si_cible_est_un_fichier(tmp_path):
    """Si la cible existe et n'est pas un répertoire, l'erreur est relevée."""
    fichier = tmp_path / "fichier.txt"
    fichier.write_text("x")
    with pytest.raises(OSError):
        mkdir_p(str(fichier))


def test_supprime_repertoire_vide(tmp_path):
    """Un répertoire vide est supprimé."""
    vide = tmp_path / "vide"
    vide.mkdir()
    supprime(str(vide))
    assert not vide.exists()


def test_supprime_repertoire_non_vide_conserve(tmp_path):
    """Un répertoire non vide n'est pas supprimé (sans force)."""
    plein = tmp_path / "plein"
    plein.mkdir()
    (plein / "f.txt").write_text("x")
    supprime(str(plein))
    assert plein.exists()


def test_remonte_arborescence_renvoie_les_parents(tmp_path):
    """Le générateur remonte les parents relatifs à la racine, hors racine."""
    fichier = tmp_path / "a" / "b" / "c.txt"
    parents = list(remonte_arborescence(fichier, racine=tmp_path))
    assert parents == [tmp_path / "a" / "b", tmp_path / "a"]


def test_remonte_arborescence_hors_racine_leve(tmp_path):
    """Un fichier non rattaché à la racine lève ValueError."""
    with pytest.raises(ValueError):
        list(remonte_arborescence(Path("/autre/chemin/x.txt"), racine=tmp_path))


def test_iter_fichiers_sur_repertoire(tmp_path):
    """Sur un répertoire, tous les fichiers sont listés récursivement."""
    (tmp_path / "sous").mkdir()
    f1 = tmp_path / "a.txt"
    f2 = tmp_path / "sous" / "b.txt"
    f1.write_text("1")
    f2.write_text("2")
    resultat = iter_fichiers(tmp_path)
    assert set(resultat) == {f1, f2}
    # aucun répertoire dans le résultat
    assert all(not p.is_dir() for p in resultat)


def test_iter_fichiers_sur_fichier_unique(tmp_path):
    """Sur un fichier, seul ce fichier est renvoyé."""
    f = tmp_path / "seul.txt"
    f.write_text("x")
    assert iter_fichiers(f) == [f]
