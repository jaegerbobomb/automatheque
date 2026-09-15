# -*- coding: utf-8 -*-
"""Tests de l'exécution parallèle bornée (#47)."""

import logging
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


# --- Compte rendu au fil de l'eau : `a_chaque_resultat` ---------------------


def test_le_crochet_est_appele_une_fois_par_element():
    vus = []

    res = parallelise(
        lambda x: x * 2, [1, 2, 3], workers=2, a_chaque_resultat=vus.append
    )

    assert sorted(r.valeur for r in vus) == [2, 4, 6]
    assert [r.valeur for r in res] == [2, 4, 6]


def test_le_crochet_voit_aussi_les_echecs():
    def peut_echouer(x):
        if x == 3:
            raise ValueError("trois interdit")
        return x

    vus = []
    parallelise(peut_echouer, [1, 3], workers=2, a_chaque_resultat=vus.append)

    echecs = [r for r in vus if not r.reussi]
    assert len(echecs) == 1
    assert isinstance(echecs[0].erreur, ValueError)


def test_le_crochet_suit_l_achevement_pas_l_ordre_des_elements():
    """Tout l'intérêt du crochet : ne pas attendre le premier élément.

    Le premier élément n'est libéré qu'une fois les deux autres passés par le
    crochet — sans temporisation, donc sans dépendre des vitesses relatives.
    """
    vus = []
    libere = threading.Event()

    def attend_les_autres(x):
        if x == 0:
            libere.wait(timeout=5)
        return x

    def note(resultat):
        vus.append(resultat)
        if len(vus) == 2:
            libere.set()

    res = parallelise(attend_les_autres, [0, 1, 2], workers=3, a_chaque_resultat=note)

    # La valeur de retour garde l'ordre des éléments…
    assert [r.valeur for r in res] == [0, 1, 2]
    # …le crochet, lui, suit l'achèvement.
    assert vus[-1].element == 0


def test_le_crochet_s_execute_dans_le_thread_appelant():
    """Donc l'appelant n'a pas de verrou à prévoir autour de son compteur."""
    threads = set()

    parallelise(
        lambda x: x,
        [1, 2, 3],
        workers=3,
        a_chaque_resultat=lambda _: threads.add(threading.current_thread().ident),
    )

    assert threads == {threading.current_thread().ident}


def test_le_crochet_marche_aussi_en_mode_processus():
    """Un compteur incrémenté dans `fonction` resterait dans le sous-processus ;
    le crochet, lui, s'exécute côté parent — et n'a pas à être picklable."""
    vus = []

    res = parallelise(abs, [-1, -2, 3], processus=True, a_chaque_resultat=vus.append)

    assert sorted(r.valeur for r in vus) == [1, 2, 3]
    assert [r.valeur for r in res] == [1, 2, 3]


def test_un_crochet_qui_leve_n_interrompt_pas_les_taches(caplog):
    def rate(_resultat):
        raise RuntimeError("compte rendu cassé")

    with caplog.at_level(logging.WARNING, logger="automatheque.util.parallele"):
        res = parallelise(lambda x: x * 2, [1, 2, 3], workers=2, a_chaque_resultat=rate)

    assert [r.valeur for r in res] == [2, 4, 6]
    assert sum("a_chaque_resultat" in r.getMessage() for r in caplog.records) == 3
