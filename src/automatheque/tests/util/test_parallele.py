# -*- coding: utf-8 -*-
"""Tests de l'exécution parallèle bornée (#47)."""

import threading
import time

import pytest
from automatheque.util import Resultat, parallelise


def test_applique_la_fonction_et_preserve_l_ordre():
    res = parallelise(lambda x: x * 10, [1, 2, 3], workers=3)
    assert [r.valeur for r in res] == [10, 20, 30]
    assert all(isinstance(r, Resultat) and r.reussi for r in res)


def test_ordre_preserve_malgre_des_durees_differentes():
    """Le premier élément est le plus lent : il finit dernier mais reste 1er."""

    def lent_si_zero(x):
        time.sleep(0.03 if x == 0 else 0)
        return x

    res = parallelise(lent_si_zero, [0, 1, 2], workers=3)
    assert [r.valeur for r in res] == [0, 1, 2]


def test_les_erreurs_sont_collectees_par_tache_pas_un_arret_brutal():
    def peut_echouer(x):
        if x == 2:
            raise ValueError("deux interdit")
        return x * 10

    res = parallelise(peut_echouer, [1, 2, 3], workers=3)
    assert res[0].reussi and res[0].valeur == 10
    assert not res[1].reussi and isinstance(res[1].erreur, ValueError)
    assert res[2].reussi and res[2].valeur == 30


def test_valeur_ou_leve():
    res = parallelise(lambda x: 1 / x, [1, 0], workers=2)
    assert res[0].valeur_ou_leve() == 1
    with pytest.raises(ZeroDivisionError):
        res[1].valeur_ou_leve()


def test_execute_reellement_en_parallele():
    """`Barrier(4)` ne se débloque que si les 4 tâches y arrivent **ensemble** ;
    sans parallélisme réel, `wait()` expirerait (`BrokenBarrierError`)."""
    barriere = threading.Barrier(4, timeout=5)

    def rejoint_les_autres(x):
        barriere.wait()
        return x

    res = parallelise(rejoint_les_autres, range(4), workers=4)
    assert [r.valeur for r in res] == [0, 1, 2, 3]
    assert all(r.reussi for r in res)


def test_debit_limite_la_cadence_de_depart():
    debut = time.monotonic()
    res = parallelise(lambda x: x, range(4), workers=4, debit=20)  # 20/s → 0.05s
    ecoule = time.monotonic() - debut
    assert all(r.reussi for r in res)
    # 4 départs espacés de 0.05s = 3 intervalles = 0.15s (marge : >= 0.12).
    assert ecoule >= 0.12


def test_mode_processus_avec_une_fonction_picklable():
    # `abs` est un builtin picklable : évite les soucis d'import du module de
    # test par les sous-processus.
    res = parallelise(abs, [-1, -2, 3], processus=True)
    assert [r.valeur for r in res] == [1, 2, 3]


def test_liste_vide_renvoie_une_liste_vide():
    assert parallelise(lambda x: x, []) == []


def test_parametres_invalides():
    with pytest.raises(ValueError):
        parallelise(lambda x: x, [1], workers=0)
    with pytest.raises(ValueError):
        parallelise(lambda x: x, [1], debit=0)
