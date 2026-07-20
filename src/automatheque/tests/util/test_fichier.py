# -*- coding: utf-8 -*-
"""Tests des utilitaires de manipulation des fichiers (util/fichier.py)."""

import automatheque.util.fichier as fichier
from automatheque.util.fichier import enleve_caracteres_invalides


def test_remplace_le_slash_par_underscore():
    """Le seul caractère invalide sous Linux (le slash) devient un underscore."""
    assert enleve_caracteres_invalides("a/b/c") == "a_b_c"


def test_conserve_les_autres_caracteres_speciaux():
    """Sous Linux, les autres caractères "spéciaux" sont conservés tels quels."""
    valeur = 'nom:*?"<>|.txt'
    assert enleve_caracteres_invalides(valeur) == valeur


def test_chaine_sans_caractere_invalide_inchangee():
    """Une chaîne propre est renvoyée à l'identique."""
    assert enleve_caracteres_invalides("fichier_normal.txt") == "fichier_normal.txt"


def test_valeur_non_chaine_renvoyee_telle_quelle():
    """Un int (sans méthode replace) est renvoyé sans lever d'exception."""
    assert enleve_caracteres_invalides(42) == 42


def test_posix_ne_retire_que_le_separateur(monkeypatch):
    """#25 : sous POSIX, seul le séparateur est invalide."""
    monkeypatch.setattr(fichier.os, "name", "posix")
    assert enleve_caracteres_invalides("a:b*c?/d") == "a:b*c?_d"


def test_windows_retire_tous_les_caracteres_interdits(monkeypatch):
    """#25 : sous Windows, l'ensemble étendu des caractères interdits est retiré."""
    monkeypatch.setattr(fichier.os, "name", "nt")
    assert enleve_caracteres_invalides('a/b\\c:d*e?f"g<h>i|j') == (
        "a_b_c_d_e_f_g_h_i_j"
    )
