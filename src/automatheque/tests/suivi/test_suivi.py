"""Tests du sous-système ``suivi`` : port, adaptateur répertoire et journal."""

import pytest
from automatheque.suivi.adaptateurs.repertoire import StockageRepertoire
from automatheque.suivi.journal import JournalSuivi
from automatheque.suivi.ports import StockageAbstraite

# --- Port abstrait -----------------------------------------------------------


def test_stockage_abstraite_non_instanciable():
    """On ne peut pas instancier directement le port abstrait."""
    with pytest.raises(TypeError):
        StockageAbstraite()


def test_stockage_abstraite_methodes_levent_notimplemented():
    """Les méthodes du port lèvent ``NotImplementedError`` si appelées via super()."""

    class StockageBidon(StockageAbstraite):
        def existe(self, reference):
            return super().existe(reference)

        def sauvegarde(self, reference, contenu):
            return super().sauvegarde(reference, contenu)

    s = StockageBidon()
    with pytest.raises(NotImplementedError):
        s.existe("x")
    with pytest.raises(NotImplementedError):
        s.sauvegarde("x", "y")


# --- Adaptateur StockageRepertoire ------------------------------------------


def test_repertoire_cree_le_dossier(tmp_path):
    """``__attrs_post_init__`` crée le répertoire (y compris les parents)."""
    cible = tmp_path / "sous" / "dossier"
    assert not cible.exists()
    StockageRepertoire(cible)
    assert cible.is_dir()


def test_repertoire_est_un_stockage_abstraite(tmp_path):
    assert isinstance(StockageRepertoire(tmp_path), StockageAbstraite)


def test_repertoire_existe_faux_puis_vrai(tmp_path):
    stockage = StockageRepertoire(tmp_path)
    assert stockage.existe("ref1") is False
    assert stockage.sauvegarde("ref1", "contenu") is True
    assert stockage.existe("ref1") is True


def test_repertoire_sauvegarde_ecrit_le_contenu(tmp_path):
    stockage = StockageRepertoire(tmp_path)
    stockage.sauvegarde("maref", "des données")
    assert (tmp_path / "maref").read_text() == "des données"


def test_repertoire_sauvegarde_ecrase_le_contenu(tmp_path):
    stockage = StockageRepertoire(tmp_path)
    stockage.sauvegarde("maref", "v1")
    stockage.sauvegarde("maref", "v2")
    assert (tmp_path / "maref").read_text() == "v2"


# --- JournalSuivi ------------------------------------------------------------


def test_journal_deja_fait_et_coche(tmp_path):
    """Round-trip complet : rien fait, puis coché, puis déjà fait."""
    journal = JournalSuivi(StockageRepertoire(tmp_path))
    assert journal.deja_fait("action42") is False
    assert journal.coche("action42", "résultat") is True
    assert journal.deja_fait("action42") is True


def test_journal_idempotence(tmp_path):
    """Cocher deux fois reste cohérent : l'action est vue comme faite."""
    journal = JournalSuivi(StockageRepertoire(tmp_path))
    journal.coche("act", "a")
    journal.coche("act", "b")
    assert journal.deja_fait("act") is True
    assert (tmp_path / "act").read_text() == "b"


def test_journal_references_independantes(tmp_path):
    journal = JournalSuivi(StockageRepertoire(tmp_path))
    journal.coche("faite", "x")
    assert journal.deja_fait("faite") is True
    assert journal.deja_fait("pas_faite") is False


def test_journal_ni_fait_ni_a_refaire_est_neutre(tmp_path):
    """La méthode ``ni_fait_ni_à_refaire`` n'est pas implémentée (renvoie None)."""
    journal = JournalSuivi(StockageRepertoire(tmp_path))
    assert journal.ni_fait_ni_à_refaire("arg") is None


def test_journal_stockage_par_defaut(tmp_path):
    """Le stockage par défaut est un ``StockageRepertoire``."""
    journal = JournalSuivi()
    assert isinstance(journal.stockage, StockageRepertoire)
