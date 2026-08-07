# -*- coding: utf-8 -*-
"""Tests du renommage.

L'ancien dépôt n'avait aucune couverture sur ce module, alors que c'est
précisément son comportement de rangement que les applications doivent
préserver. Ces tests sont écrits à la remontée.
"""

import configparser
import os

import attr
import pytest
from automatheque.renommage import (
    AucunGabaritApplicable,
    ConditionInvalide,
    Gabarit,
    GabaritInapplicable,
    Gabarits,
    Renommable,
    Renommeur,
    TransfertIncomplet,
    evalue_condition,
)


@attr.s
class Photo(Renommable):
    """Un renommable minimal."""

    album = attr.ib(default="", kw_only=True)
    annee = attr.ib(default="", kw_only=True)
    pays = attr.ib(default="", kw_only=True)

    @classmethod
    def _gabarits_par_defaut(cls):
        return Gabarits(
            [
                Gabarit(squelette="{annee}/{album}/{nom}", condition='"{album}"'),
                Gabarit(squelette="a-trier/{nom}", ordre=9),
            ]
        )

    def _liste_champs_dispo(self):
        return {
            "album": self.album,
            "annee": self.annee,
            "pays": self.pays,
            "nom": os.path.basename(self.filename),
        }


@pytest.fixture
def photo(tmp_path):
    """Une photo posée sur le disque, prête à être rangée."""
    fichier = tmp_path / "source" / "DSC_0001.jpg"
    fichier.parent.mkdir()
    fichier.write_bytes(b"des octets de photo")
    return Photo(filename=str(fichier), album="Japon", annee="2013")


#
# Gabarits
#


def test_gabarit_sans_condition_s_applique_toujours():
    gabarits = Gabarits([Gabarit(squelette="a-trier/{nom}")])
    assert gabarits.choisit_gabarit(Photo()).squelette == "a-trier/{nom}"


def test_gabarit_avec_condition_vraie_passe_avant_celui_sans_condition():
    photo = Photo(filename="/a/b.jpg", album="Japon", annee="2013")
    assert (
        photo._gabarits_par_defaut()
        .choisit_gabarit(photo)
        .squelette.startswith("{annee}")
    )


def test_gabarit_avec_condition_fausse_est_ecarte():
    photo = Photo(filename="/a/b.jpg", album="", annee="2013")
    assert (
        photo._gabarits_par_defaut().choisit_gabarit(photo).squelette == "a-trier/{nom}"
    )


def test_les_conditions_vraies_sont_classees_par_ordre():
    gabarits = Gabarits(
        [
            Gabarit(squelette="tard", condition='"oui"', ordre=5),
            Gabarit(squelette="tot", condition='"oui"', ordre=1),
        ]
    )
    assert gabarits.choisit_gabarit(Photo()).squelette == "tot"


def test_sans_aucun_gabarit_applicable():
    gabarits = Gabarits([Gabarit(squelette="jamais", condition='"" and "x"')])
    with pytest.raises(AucunGabaritApplicable):
        gabarits.choisit_gabarit(Photo())


def test_aucun_gabarit_applicable_reste_un_value_error():
    """Rétro-compat : le code d'origine levait un `ValueError` nu."""
    assert issubclass(AucunGabaritApplicable, ValueError)


def test_condition_referencant_un_champ_absent_est_fausse():
    """Elle n'interrompt pas le choix : le gabarit suivant est essayé."""
    gabarits = Gabarits(
        [
            Gabarit(squelette="jamais", condition='"{champ_inconnu}"'),
            Gabarit(squelette="filet", ordre=9),
        ]
    )
    assert gabarits.choisit_gabarit(Photo()).squelette == "filet"


def test_gabarits_est_iterable_et_mesurable():
    gabarits = Gabarits()
    gabarits.append(Gabarit(squelette="a"))
    gabarits.append(Gabarit(squelette="b"))
    assert len(gabarits) == 2
    assert [g.squelette for g in gabarits] == ["a", "b"]


def test_json_expose_les_gabarits():
    gabarits = Gabarits([Gabarit(squelette="a", condition="", ordre=3)])
    assert gabarits.__json__() == [{"squelette": "a", "condition": "", "ordre": 3}]


#
# Conditions
#


def test_evalue_condition_litteraux_et_operateurs():
    assert evalue_condition('"Osaka" and "JP"')
    assert not evalue_condition('"" and "JP"')
    assert evalue_condition('"JP" != "FR"')
    assert not evalue_condition('"FR" != "FR"')
    assert evalue_condition('not ""')
    assert evalue_condition('"a" or ""')


def test_evalue_condition_refuse_un_appel():
    """Régression : les champs viennent des métadonnées des fichiers traités.

    Le code d'origine passait la condition formatée à `eval()` : un fichier
    dont l'album portait le bon texte faisait exécuter du code arbitraire.
    """
    with pytest.raises(ConditionInvalide):
        evalue_condition('__import__("os").system("echo compromis")')


def test_evalue_condition_refuse_un_nom():
    with pytest.raises(ConditionInvalide):
        evalue_condition("open")


def test_evalue_condition_refuse_un_acces_attribut():
    with pytest.raises(ConditionInvalide):
        evalue_condition('"".__class__')


def test_evalue_condition_refuse_une_expression_mal_formee():
    with pytest.raises(ConditionInvalide):
        evalue_condition('"Osaka" and and')


def test_injection_par_les_metadonnees_ne_s_execute_pas():
    """Bout en bout : un album malveillant ne fait qu'invalider la condition."""
    photo = Photo(filename="/a/b.jpg", album='" and __import__("os").getcwd() and "')
    gabarits = Gabarits(
        [
            Gabarit(squelette="dangereux", condition='"{album}"'),
            Gabarit(squelette="filet", ordre=9),
        ]
    )
    assert gabarits.choisit_gabarit(photo).squelette == "filet"


#
# Configuration reçue, et non chargée
#


def _config(texte):
    config = configparser.ConfigParser()
    config.read_string(texte)
    return config


def test_gabarits_depuis_configuration():
    config = _config(
        "[renommage]\n"
        "r1 = ['{annee}/{album}/{nom}', '\"{album}\"', 1]\n"
        "r2 = ['a-trier/{nom}', '', 9]\n"
    )
    gabarits = Gabarits.depuis_configuration(config)
    assert len(gabarits) == 2
    assert [g.ordre for g in gabarits] == [1, 9]
    assert list(gabarits)[0].squelette == "{annee}/{album}/{nom}"


def test_gabarits_depuis_configuration_section_choisie():
    config = _config("[rangement_photos]\nr1 = ['{nom}', '', 1]\n")
    assert len(Gabarits.depuis_configuration(config, "rangement_photos")) == 1


def test_gabarits_depuis_configuration_option_illisible():
    config = _config("[renommage]\nr1 = pas un triplet\n")
    with pytest.raises(ValueError):
        Gabarits.depuis_configuration(config)


def test_configuration_n_execute_pas_de_code():
    """`literal_eval`, pas `eval` : un fichier de conf décrit des données."""
    config = _config('[renommage]\nr1 = __import__("os").getcwd()\n')
    with pytest.raises(ValueError):
        Gabarits.depuis_configuration(config)


def test_renommeur_ne_consulte_aucune_configuration_globale(photo, tmp_path):
    """Les gabarits fournis explicitement sont les seuls utilisés."""
    gabarits = Gabarits([Gabarit(squelette="explicite/{nom}")])
    cible = Renommeur(photo, gabarits=gabarits).renomme(str(tmp_path / "cible"))
    assert cible.endswith(os.path.join("explicite", "DSC_0001.jpg"))


def test_renommeur_retombe_sur_les_gabarits_par_defaut(photo, tmp_path):
    cible = Renommeur(photo).renomme(str(tmp_path / "cible"))
    assert cible.endswith(os.path.join("2013", "Japon", "DSC_0001.jpg"))


def test_renommeur_refuse_un_objet_non_renommable():
    with pytest.raises(ValueError):
        Renommeur(object())


#
# Déplacement
#


def test_renomme_deplace_le_fichier(photo, tmp_path):
    origine = photo.filename
    cible = photo.renomme(str(tmp_path / "cible"))

    assert os.path.exists(cible)
    assert not os.path.exists(origine)
    assert photo.filename == cible
    assert open(cible, "rb").read() == b"des octets de photo"


def test_renomme_cree_l_arborescence(photo, tmp_path):
    cible = photo.renomme(str(tmp_path / "cible"))
    assert cible == str(tmp_path / "cible" / "2013" / "Japon" / "DSC_0001.jpg")


def test_renomme_en_copiant_conserve_l_original(photo, tmp_path):
    origine = photo.filename
    cible = photo.renomme(str(tmp_path / "cible"), copier=True)
    assert os.path.exists(origine)
    assert os.path.exists(cible)


def test_debug_ne_deplace_rien_mais_annonce_la_cible(photo, tmp_path):
    origine = photo.filename
    cible = photo.renomme(str(tmp_path / "cible"), debug=True)

    assert cible.endswith(os.path.join("2013", "Japon", "DSC_0001.jpg"))
    assert not os.path.exists(cible)
    assert os.path.exists(origine)


def test_debug_ne_deplace_pas_l_objet_non_plus(photo, tmp_path):
    """Régression : `filename` était réaffecté avant même la copie."""
    origine = photo.filename
    photo.renomme(str(tmp_path / "cible"), debug=True)
    assert photo.filename == origine


def test_cible_existante_n_est_pas_ecrasee(photo, tmp_path):
    existant = tmp_path / "cible" / "2013" / "Japon" / "DSC_0001.jpg"
    existant.parent.mkdir(parents=True)
    existant.write_bytes(b"deja la")

    origine = photo.filename
    photo.renomme(str(tmp_path / "cible"))

    assert existant.read_bytes() == b"deja la"
    assert os.path.exists(origine)
    assert photo.filename == origine


def test_force_ecrase_la_cible_existante(photo, tmp_path):
    existant = tmp_path / "cible" / "2013" / "Japon" / "DSC_0001.jpg"
    existant.parent.mkdir(parents=True)
    existant.write_bytes(b"deja la")

    photo.renomme(str(tmp_path / "cible"), force=True)
    assert existant.read_bytes() == b"des octets de photo"


def test_transfert_incomplet_conserve_l_original(photo, tmp_path, monkeypatch):
    """Si la copie tronque, on ne supprime surtout pas la source."""

    def copie_tronquee(source, cible):
        with open(cible, "wb") as f:
            f.write(b"tronque")

    monkeypatch.setattr("shutil.copy", copie_tronquee)

    origine = photo.filename
    with pytest.raises(TransfertIncomplet):
        photo.renomme(str(tmp_path / "cible"))
    assert os.path.exists(origine)


def test_squelette_referencant_un_champ_absent(photo, tmp_path):
    gabarits = Gabarits([Gabarit(squelette="{champ_inconnu}/{nom}")])
    with pytest.raises(GabaritInapplicable):
        photo.renomme(str(tmp_path / "cible"), gabarits=gabarits)


def test_renommable_sans_surcharge_annonce_ce_qui_manque():
    with pytest.raises(NotImplementedError):
        Renommable._gabarits_par_defaut()
    with pytest.raises(NotImplementedError):
        Renommable()._liste_champs_dispo()


@pytest.mark.skipif(
    not hasattr(os, "listxattr"), reason="attributs étendus absents de la plateforme"
)
def test_aucun_attribut_etendu_n_est_ecrit(photo, tmp_path):
    """Le renommage n'écrit plus de xattr : la provenance va ailleurs."""
    cible = photo.renomme(str(tmp_path / "cible"))
    assert not os.listxattr(cible)
