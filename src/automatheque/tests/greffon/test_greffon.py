from automatheque.greffon import fabrique_greffon, Greffon


class TestGreffon(Greffon):
    CAPACITES = ["TEST_CAPACITE"]
    pass


class TestGreffon2(Greffon):
    CAPACITES = ["TEST_CAPACITE2"]
    pass


def test_greffon_identifiant():
    assert list(fabrique_greffon._monteurs.keys()) == []

    fabrique_greffon.enregistre_monteur(TestGreffon.cle, TestGreffon)
    assert list(fabrique_greffon._monteurs.keys()) == ["test"]
    fabrique_greffon.enregistre_monteur(TestGreffon2.cle, TestGreffon2)
    assert list(fabrique_greffon._monteurs.keys()) == [
        "test",
        "test2",
    ]
    assert issubclass(fabrique_greffon._monteurs["test"], TestGreffon)
    assert issubclass(fabrique_greffon._monteurs["test2"], TestGreffon2)

    tt = fabrique_greffon.cree(TestGreffon.cle)
    assert len(Greffon.greffons_identifiants()) == 1
    assert isinstance(tt, TestGreffon)
    assert tt.identifiant in Greffon.greffons_identifiants()
    assert Greffon.greffon_par_identifiant(identifiant=tt.identifiant) is tt

    tt2 = fabrique_greffon.active(TestGreffon2.cle)

    assert len(Greffon.greffons_identifiants()) == 2
    assert Greffon.greffon_par_identifiant(identifiant=tt2.identifiant) is not tt
    assert isinstance(tt2, TestGreffon2)

    tt_ = Greffon.greffons_par_capacite("TEST_CAPACITE")[0]
    assert tt_ is tt
