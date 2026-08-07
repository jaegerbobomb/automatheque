# -*- coding: utf-8 -*-
"""Tests de la décomposition.

L'ancien dépôt n'avait aucune couverture sur ce module : ces tests sont
écrits à la remontée, et fixent le comportement que les consommateurs
attendent.
"""

import re

import attr
import pytest
from automatheque.decomposition import (
    DECOMPOSE_ANALYSE_ARBO_COMPLETE,
    DECOMPOSE_ANALYSE_ARBO_CONCATENE,
    DECOMPOSE_RESULTAT_CUMULE,
    DECOMPOSE_RESULTAT_MAX_INFOS,
    DECOMPOSE_RESULTAT_PREMIER_NON_NUL,
    Decomposable,
    Decomposeur,
    Decomposeurs,
    DecompositionEchecTousPatrons,
    Identificateur,
)
from automatheque.exceptions import ArgumentManquant


def _remplit_serie(obj, resultats):
    """Appel en retour : reverse le tuple trouvé dans l'objet."""
    obj.serie, obj.saison, obj.episode = resultats


def _remplit_annee(obj, resultats):
    obj.annee = resultats


@attr.s
class SerieDecomposeurs(Decomposeurs):
    """Un jeu de patrons pour les séries."""

    def __attrs_post_init__(self):
        self.decomposeurs = [
            Decomposeur(r"(.+)[. ]S(\d{2})E(\d{2})", _remplit_serie, drapeaux=re.I),
        ]


@attr.s
class Episode(Decomposable):
    """Objet décomposable minimal."""

    filename = attr.ib(default="")
    basename = attr.ib(default="")
    serie = attr.ib(default=None)
    saison = attr.ib(default=None)
    episode = attr.ib(default=None)
    annee = attr.ib(default=None)


@attr.s
class EpisodeAvecDefaut(Episode):
    """Décomposable qui sait fournir ses patrons par défaut."""

    @classmethod
    def _decomposeurs_par_defaut(cls):
        return SerieDecomposeurs()


def test_decompose_le_basename():
    ep = Episode(filename="/media/Ma.Serie.S01E02.avi", basename="Ma.Serie.S01E02.avi")
    ep.decompose(decomposeurs=SerieDecomposeurs())
    assert (ep.serie, ep.saison, ep.episode) == ("Ma.Serie", "01", "02")


def test_decompose_renvoie_le_resultat_du_premier_patron():
    ep = Episode(basename="Ma.Serie.S01E02.avi")
    assert ep.decompose(decomposeurs=SerieDecomposeurs()) == ("Ma.Serie", "01", "02")


def test_decompose_sans_patron_applicable_leve_l_echec():
    ep = Episode(basename="rien-a-decomposer.txt")
    with pytest.raises(DecompositionEchecTousPatrons):
        ep.decompose(decomposeurs=SerieDecomposeurs())


def test_decomposeurs_par_defaut_utilises_si_non_precises():
    ep = EpisodeAvecDefaut(basename="Ma.Serie.S01E02.avi")
    ep.decompose()
    assert ep.serie == "Ma.Serie"


def test_sans_decomposeurs_ni_defaut_on_reclame_l_argument():
    ep = Episode(basename="Ma.Serie.S01E02.avi")
    with pytest.raises(ArgumentManquant):
        ep.decompose()


def test_decomposeurs_donnes_par_chemin_d_import():
    ep = Episode(basename="Ma.Serie.S01E02.avi")
    ep.decompose(decomposeurs="{}.SerieDecomposeurs".format(__name__))
    assert ep.serie == "Ma.Serie"


def test_chemin_d_import_introuvable_reclame_l_argument():
    ep = Episode(basename="Ma.Serie.S01E02.avi")
    with pytest.raises(ArgumentManquant):
        Identificateur(ep, decomposeurs="paquet.inexistant.PasDeClasse")


def test_appel_source_explicite_est_utilise():
    """Régression : un `appel_source` fourni levait un `UnboundLocalError`."""

    def source_figee(obj, valeur):
        return "Autre.Serie.S03E04.avi"

    decomposeurs = SerieDecomposeurs()
    decomposeurs.decomposeurs = [
        Decomposeur(
            r"(.+)[. ]S(\d{2})E(\d{2})", _remplit_serie, appel_source=source_figee
        )
    ]

    ep = Episode(basename="ignore.avi")
    ep.decompose(decomposeurs=decomposeurs)
    assert (ep.serie, ep.saison, ep.episode) == ("Autre.Serie", "03", "04")


def test_analyse_arborescence_complete_remonte_les_niveaux():
    """Le patron ne matche aucun niveau seul, mais matche un répertoire."""
    ep = Episode(
        filename="/media/series/Ma.Serie.S01E02/video.avi", basename="video.avi"
    )
    ep.decompose(
        racine="/media",
        decomposeurs=SerieDecomposeurs(),
        options_analyse=DECOMPOSE_ANALYSE_ARBO_COMPLETE,
    )
    assert (ep.serie, ep.saison, ep.episode) == ("Ma.Serie", "01", "02")


def test_analyse_arborescence_concatenee():
    """Aucun niveau ne porte l'information complète, leur concaténation si."""
    ep = Episode(filename="/media/series/Ma.Serie/S01E02.avi", basename="S01E02.avi")
    ep.decompose(
        racine="/media",
        decomposeurs=SerieDecomposeurs(),
        options_analyse=DECOMPOSE_ANALYSE_ARBO_CONCATENE,
    )
    assert (ep.serie, ep.saison, ep.episode) == ("Ma.Serie", "01", "02")


def test_options_analyse_acceptent_une_collection():
    ep = Episode(
        filename="/media/series/Ma.Serie.S01E02/video.avi", basename="video.avi"
    )
    ep.decompose(
        racine="/media",
        decomposeurs=SerieDecomposeurs(),
        options_analyse=[
            DECOMPOSE_ANALYSE_ARBO_COMPLETE,
            DECOMPOSE_ANALYSE_ARBO_CONCATENE,
        ],
    )
    assert ep.serie == "Ma.Serie"


def test_resultat_cumule_applique_tous_les_patrons():
    decomposeurs = SerieDecomposeurs()
    decomposeurs.decomposeurs.append(Decomposeur(r"\((\d{4})\)", _remplit_annee))

    ep = Episode(basename="Ma.Serie.S01E02 (2019).avi")
    ep.decompose(decomposeurs=decomposeurs, options_resultat=DECOMPOSE_RESULTAT_CUMULE)
    assert ep.serie == "Ma.Serie"
    assert ep.annee == "2019"


def test_resultat_premier_non_nul_s_arrete_au_premier():
    decomposeurs = SerieDecomposeurs()
    decomposeurs.decomposeurs.append(Decomposeur(r"\((\d{4})\)", _remplit_annee))

    ep = Episode(basename="Ma.Serie.S01E02 (2019).avi")
    ep.decompose(
        decomposeurs=decomposeurs,
        options_resultat=DECOMPOSE_RESULTAT_PREMIER_NON_NUL,
    )
    assert ep.serie == "Ma.Serie"
    assert ep.annee is None


def test_resultat_max_infos_garde_la_decomposition_la_plus_riche():
    """Deux patrons matchent ; celui qui remplit trois champs doit gagner."""

    def _remplit_serie_seule(obj, resultats):
        obj.serie = resultats

    decomposeurs = SerieDecomposeurs()
    # Le patron « pauvre » est joué en premier : sans le calcul de score, c'est
    # lui qui resterait.
    decomposeurs.decomposeurs.insert(
        0, Decomposeur(r"^([^.]+)\.", _remplit_serie_seule)
    )

    ep = Episode(basename="Ma.Serie.S01E02.avi")
    ep.decompose(
        decomposeurs=decomposeurs, options_resultat=DECOMPOSE_RESULTAT_MAX_INFOS
    )
    assert (ep.serie, ep.saison, ep.episode) == ("Ma.Serie", "01", "02")


def test_auto_decompose_trouve_une_combinaison_qui_marche():
    ep = Episode(
        filename="/media/series/Ma.Serie.S01E02/video.avi", basename="video.avi"
    )
    ep.auto_decompose(racine="/media", decomposeurs=SerieDecomposeurs())
    assert ep.serie == "Ma.Serie"


def test_auto_decompose_echoue_si_rien_ne_marche():
    ep = Episode(filename="/media/series/rien/video.avi", basename="video.avi")
    with pytest.raises(DecompositionEchecTousPatrons):
        ep.auto_decompose(racine="/media", decomposeurs=SerieDecomposeurs())


def test_prepare_decomposition_par_defaut_renvoie_le_basename():
    ep = Episode(basename="video.avi")
    assert ep._prepare_decomposition() == "video.avi"
    assert ep._prepare_decomposition("autre") == "autre"


def test_decomposeurs_est_iterable():
    decomposeurs = SerieDecomposeurs()
    assert len(list(decomposeurs)) == 1


def test_decomposable_sans_surcharge_annonce_l_absence_de_defaut():
    with pytest.raises(NotImplementedError):
        Decomposable._decomposeurs_par_defaut()
