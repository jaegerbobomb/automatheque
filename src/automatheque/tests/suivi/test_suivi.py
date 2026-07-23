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


def test_repertoire_verrou_par_instance(tmp_path):
    """#25 : chaque adaptateur possède son propre verrou (non partagé)."""
    a = StockageRepertoire(tmp_path)
    b = StockageRepertoire(tmp_path)
    assert a._verrou is not None
    assert a._verrou is not b._verrou


def test_repertoire_ecritures_concurrentes(tmp_path):
    """Les accès concurrents restent cohérents (sérialisés par le verrou)."""
    import threading

    stockage = StockageRepertoire(tmp_path)
    erreurs = []

    def ecrit(n):
        try:
            for i in range(50):
                stockage.sauvegarde(f"ref{n}", f"{n}-{i}")
                stockage.existe(f"ref{n}")
        except Exception as e:  # pragma: no cover - ne devrait pas arriver
            erreurs.append(e)

    fils = [threading.Thread(target=ecrit, args=(n,)) for n in range(8)]
    for f in fils:
        f.start()
    for f in fils:
        f.join()

    assert erreurs == []
    for n in range(8):
        assert stockage.existe(f"ref{n}") is True


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


# --- #27 : décorateur ni_fait_ni_à_refaire (idempotence + option date) -------


def test_ni_fait_ni_a_refaire_joue_une_seule_fois(tmp_path):
    """La fonction n'est jouée qu'une fois par référence ; ensuite → None."""
    journal = JournalSuivi(StockageRepertoire(tmp_path))
    appels = []

    @journal.ni_fait_ni_à_refaire("ref")
    def action(ref):
        appels.append(ref)
        return "fait"

    assert action(ref="a") == "fait"
    assert action(ref="a") is None  # déjà fait → non rejoué
    assert appels == ["a"]


def test_ni_fait_ni_a_refaire_references_distinctes(tmp_path):
    """Deux références différentes sont suivies indépendamment."""
    journal = JournalSuivi(StockageRepertoire(tmp_path))
    appels = []

    @journal.ni_fait_ni_à_refaire("ref")
    def action(ref):
        appels.append(ref)

    action(ref="a")
    action(ref="b")
    assert appels == ["a", "b"]


def test_ni_fait_ni_a_refaire_reference_positionnelle(tmp_path):
    """La référence est aussi extraite d'un argument positionnel."""
    journal = JournalSuivi(StockageRepertoire(tmp_path))
    appels = []

    @journal.ni_fait_ni_à_refaire("ref")
    def action(ref, autre=None):
        appels.append(ref)

    action("x")
    action("x")
    assert appels == ["x"]


def test_ni_fait_ni_a_refaire_periode_rejoue_a_chaque_jour(tmp_path):
    """Avec ``periode``, l'action redevient rejouable à chaque nouvelle date."""
    import datetime

    journal = JournalSuivi(StockageRepertoire(tmp_path))
    appels = []

    def fabrique(jour):
        @journal.ni_fait_ni_à_refaire("ref", periode="jour", date=jour)
        def action(ref):
            appels.append((ref, jour))

        return action

    j1 = datetime.date(2026, 7, 23)
    j2 = datetime.date(2026, 7, 24)
    fabrique(j1)(ref="a")
    fabrique(j1)(ref="a")  # même jour → non rejoué
    fabrique(j2)(ref="a")  # nouveau jour → rejoué
    assert appels == [("a", j1), ("a", j2)]


def test_ni_fait_ni_a_refaire_periode_inconnue_leve(tmp_path):
    journal = JournalSuivi(StockageRepertoire(tmp_path))

    @journal.ni_fait_ni_à_refaire("ref", periode="decennie")
    def action(ref):
        pass

    with pytest.raises(ValueError, match="période inconnue"):
        action(ref="a")


def test_ni_fait_ni_a_refaire_argument_absent_leve(tmp_path):
    journal = JournalSuivi(StockageRepertoire(tmp_path))

    @journal.ni_fait_ni_à_refaire("inexistant")
    def action(ref):
        pass

    with pytest.raises(KeyError, match="inexistant"):
        action(ref="a")


def test_ni_fait_ni_a_refaire_reference_avec_separateur(tmp_path):
    """Une référence contenant un `/` est assainie (pas de sous-répertoire)."""
    journal = JournalSuivi(StockageRepertoire(tmp_path))
    appels = []

    @journal.ni_fait_ni_à_refaire("ref")
    def action(ref):
        appels.append(ref)

    action(ref="rapport/2026")  # ne doit pas lever
    action(ref="rapport/2026")
    assert appels == ["rapport/2026"]


def test_journal_stockage_par_defaut(tmp_path):
    """Le stockage par défaut est un ``StockageRepertoire``."""
    journal = JournalSuivi()
    assert isinstance(journal.stockage, StockageRepertoire)
