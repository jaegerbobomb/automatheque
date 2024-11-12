from typing import Protocol

import pytest

from automatheque.greffon import Greffon, fabrique_greffon
from automatheque.greffon.capacite import Capacite


class CapaciteTest(Capacite, Protocol):
    pass


class CapaciteTest2(Capacite, Protocol):
    pass


class GreffonTest(Greffon):
    CAPACITES = [CapaciteTest]


class GreffonTest2(Greffon):
    CAPACITES = [CapaciteTest2]


class GreffonTestSTR(Greffon):
    CAPACITES = ["TEST_CAPACITE"]
    pass


class GreffonTestSTR2(Greffon):
    CAPACITES = ["TEST_CAPACITE2"]
    pass


def test_greffon_identifiant():
    assert list(fabrique_greffon._monteurs.keys()) == []

    fabrique_greffon.enregistre_monteur(GreffonTest.cle, GreffonTest)
    assert list(fabrique_greffon._monteurs.keys()) == ["test"]
    fabrique_greffon.enregistre_monteur(GreffonTest2.cle, GreffonTest2)
    assert list(fabrique_greffon._monteurs.keys()) == [
        "test",
        "test2",
    ]
    assert issubclass(fabrique_greffon._monteurs["test"], GreffonTest)
    assert issubclass(fabrique_greffon._monteurs["test2"], GreffonTest2)

    tt = fabrique_greffon.cree(GreffonTest.cle)
    assert len(Greffon.greffons_identifiants()) == 1
    assert isinstance(tt, GreffonTest)
    assert tt.identifiant in Greffon.greffons_identifiants()
    assert Greffon.greffon_par_identifiant(identifiant=tt.identifiant) is tt

    tt2 = fabrique_greffon.active(GreffonTest2.cle)

    assert len(Greffon.greffons_identifiants()) == 2
    assert Greffon.greffon_par_identifiant(identifiant=tt2.identifiant) is not tt
    assert isinstance(tt2, GreffonTest2)

    assert len(Greffon.greffons_par_capacite(CapaciteTest)) == 1
    tt_ = Greffon.greffons_par_capacite(CapaciteTest)[0]
    assert tt_ is tt

    assert len(Greffon.greffons_par_capacite(CapaciteTest2)) == 1
    tt_ = Greffon.greffons_par_capacite(CapaciteTest2)[0]
    assert tt_ is tt2

    fabrique_greffon.charge_monteurs([GreffonTestSTR])
    assert "teststr" in list(fabrique_greffon._monteurs.keys())
    fabrique_greffon.active(GreffonTestSTR.cle)
    fabrique_greffon.charge_monteurs([GreffonTestSTR2])
    fabrique_greffon.active(GreffonTestSTR.cle)

    with pytest.raises(AttributeError):
        assert len(Greffon.greffons_par_capacite("TEST_CAPACITE")) == 1
