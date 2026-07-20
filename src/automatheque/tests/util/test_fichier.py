# -*- coding: utf-8 -*-
"""Tests des utilitaires de manipulation des fichiers (util/fichier.py)."""

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
