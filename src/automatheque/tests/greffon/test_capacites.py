# -*- coding: utf-8 -*-
"""Une capacité déclarée est une capacité rendue, héritage compris (#1).

`CAPACITES` n'était qu'une étiquette : elle n'était ni cumulée sur l'héritage,
ni confrontée au code du greffon, et la recherche s'appariait sur le *nom* de la
capacité.
"""

from typing import Protocol

import pytest
from automatheque.exceptions import CapaciteNonRendue
from automatheque.greffon import Greffon
from automatheque.greffon.capacite import (
    Capacite,
    capacites_declarees,
    membres_capacite,
)


@pytest.fixture(autouse=True)
def registre_vierge():
    """Isole le registre : il est **persistant**, donc partagé entre modules."""
    Greffon.purge_instances(inclure_enfants=True)
    yield
    Greffon.purge_instances(inclure_enfants=True)


class Lire(Capacite, Protocol):
    def lire(self) -> bool: ...


class Ecrire(Capacite, Protocol):
    def ecrire(self) -> bool: ...


class GreffonLecteur(Greffon):
    CAPACITES = [Lire]

    def lire(self) -> bool:
        return True


# --- Cumul sur l'héritage ---------------------------------------------------


class GreffonLecteurEcrivain(GreffonLecteur):
    CAPACITES = [Ecrire]

    def ecrire(self) -> bool:
        return True


def test_une_sous_classe_ajoute_ses_capacites():
    greffon = GreffonLecteurEcrivain()
    # Les siennes d'abord, puis celles héritées ; aucune n'est perdue.
    assert greffon.capacites == [Ecrire, Lire]


def test_la_sous_classe_reste_trouvable_par_la_capacite_heritee():
    greffon = GreffonLecteurEcrivain()
    assert greffon in Greffon.greffons_par_capacite(Lire)
    assert greffon in Greffon.greffons_par_capacite(Ecrire)


def test_pas_de_doublon_si_la_capacite_est_redeclaree():
    class GreffonRedeclare(GreffonLecteur):
        CAPACITES = [Lire]

    assert capacites_declarees(GreffonRedeclare) == [Lire]


# --- Annoncer engage --------------------------------------------------------


def test_declarer_sans_implementer_leve_a_la_definition():
    with pytest.raises(CapaciteNonRendue) as info:
        # La classe n'est jamais définie : l'erreur tombe ici, pas chez
        # l'appelant qui l'aurait obtenue par `greffons_par_capacite`.
        class GreffonMenteur(Greffon):
            CAPACITES = [Lire]

    message = str(info.value)
    assert "GreffonMenteur" in message and "Lire" in message and "lire" in message
    # Une interface non satisfaite reste un TypeError pour qui l'attrape ainsi.
    assert isinstance(info.value, TypeError)


def test_un_membre_herite_suffit():
    """Seul compte le fait de fournir le membre, pas de le redéfinir."""

    class GreffonHeritier(GreffonLecteur):
        CAPACITES = [Lire]

    assert GreffonHeritier().lire() is True


def test_membres_capacite_ignore_la_machinerie_protocol():
    assert membres_capacite(Lire) == ["lire"]
    # Une capacité-étiquette n'exige aucun membre.
    assert membres_capacite("ETIQUETTE") == []


# --- Appariement sur l'objet, pas sur le nom --------------------------------


def test_deux_capacites_homonymes_ne_sont_pas_confondues():
    class LireAilleurs(Capacite, Protocol):
        def lire(self) -> bool: ...

    # Même `__name__` que `Lire`, comme deux protocoles de modules différents.
    LireAilleurs.__name__ = "Lire"

    lecteur = GreffonLecteur()
    assert lecteur in Greffon.greffons_par_capacite(Lire)
    assert Greffon.greffons_par_capacite(LireAilleurs) == []


class GreffonEtiquette(Greffon):
    CAPACITES = ["CAPACITE_ETIQUETTE"]


def test_capacite_etiquette_trouvable_et_inoffensive():
    etiquete = GreffonEtiquette()
    lecteur = GreffonLecteur()

    assert Greffon.greffons_par_capacite("CAPACITE_ETIQUETTE") == [etiquete]
    # Sa présence dans le registre ne perturbe pas la recherche par classe.
    assert lecteur in Greffon.greffons_par_capacite(Lire)
    assert etiquete not in Greffon.greffons_par_capacite(Lire)


# --- Non-régression du socle ------------------------------------------------


def test_les_greffons_secret_restent_trouvables():
    from automatheque.secret import GreffonSecretEnv, ResoudreSecret

    greffon = GreffonSecretEnv()
    assert greffon in Greffon.greffons_par_capacite(ResoudreSecret)
