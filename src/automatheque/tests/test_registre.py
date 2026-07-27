# -*- coding: utf-8 -*-
"""Tests des registres d'instances : dédoublonnage **sans perte d'ordre**.

Le stockage se fait dans un dict (ensemble ordonné) et non un `set` : les
instances sont donc renvoyées dans l'ordre de création. C'est ce qui rend
déterministes les recherches qui s'appuient dessus (p. ex.
`greffons_par_capacite`).
"""

import gc

from automatheque.conception.structures import (
    MetaInstancePersistanteRegistre,
    MetaInstanceRegistre,
)


def test_persistante_preserve_lordre_dinsertion():
    class R(metaclass=MetaInstancePersistanteRegistre):
        def __init__(self, nom):
            self.nom = nom

    instances = [R(str(i)) for i in range(12)]
    # mêmes objets, dans l'ordre de création (et non un ordre de set arbitraire)
    assert R._instances() == instances


def test_persistante_dedoublonne_enfants_en_preservant_lordre():
    class Base(metaclass=MetaInstancePersistanteRegistre):
        pass

    class Enfant(Base):
        pass

    a = Base()
    b = Enfant()
    c = Base()

    res = Base._instances(inclure_enfants=True)
    # les 3 instances, sans doublon
    assert set(res) == {a, b, c}
    assert len(res) == 3
    # instances propres de Base d'abord, dans l'ordre d'insertion, puis enfants
    assert res.index(a) < res.index(c) < res.index(b)


def test_weak_preserve_lordre_des_instances_vivantes():
    class RW(metaclass=MetaInstanceRegistre):
        def __init__(self, nom):
            self.nom = nom

    vivantes = [RW(str(i)) for i in range(6)]
    # une instance non référencée disparaît du registre (weak ref) : on ne garde
    # que les vivantes, et dans l'ordre de création.
    RW("ephemere")
    gc.collect()
    assert RW._instances() == vivantes
