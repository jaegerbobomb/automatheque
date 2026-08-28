# -*- coding: utf-8 -*-
"""Deux rangements vers le même nom : un seul gagne, aucun fichier ne disparaît.

Le renommeur est fait pour être appelé depuis plusieurs fils d'exécution — c'est
ce que fait tout consommateur qui range une arborescence avec un pool. Deux
fichiers différents peuvent produire le **même** chemin cible ; il faut alors en
ranger un et refuser l'autre, sans perdre ni l'un ni l'autre.

La copie est ralentie pour ouvrir en grand la fenêtre entre le moment où la
cible est jugée libre et celui où elle existe. On ne fabrique pas la course :
on la rend reproductible.
"""

import os
import shutil
import threading
import time

import attr
from automatheque.renommage import Gabarit, Gabarits, Renommable, Renommeur
from automatheque.renommage import renommeur as module_renommeur

CIBLE = "cible.bin"
TAILLE = 64 * 1024
LENTEUR = 0.3  # bien au-dessus du bruit d'ordonnancement


@attr.s
class FichierRenommable(Renommable):
    """Le plus petit `Renommable` possible : un chemin, et un nom fixe."""

    source = attr.ib(default="")

    @classmethod
    def _gabarits_par_defaut(cls):
        return Gabarits([Gabarit(squelette=CIBLE)])

    def _liste_champs_dispo(self):
        return {}


def test_deux_rangements_simultanes_vers_la_meme_cible(tmp_path, monkeypatch):
    source = tmp_path / "entrant"
    source.mkdir()
    contenus = {}
    for numero in (0, 1):
        chemin = source / "f{}.bin".format(numero)
        chemin.write_bytes(bytes([numero]) * TAILLE)
        contenus[str(chemin)] = chemin.read_bytes()
    cible = tmp_path / "range"
    cible.mkdir()

    copie = shutil.copy

    def copie_lente(origine, destination, *args, **kwargs):
        time.sleep(LENTEUR)
        return copie(origine, destination, *args, **kwargs)

    monkeypatch.setattr(module_renommeur.shutil, "copy", copie_lente)

    depart = threading.Barrier(2)

    def range_le_fichier(chemin):
        depart.wait()
        Renommeur(FichierRenommable(source=chemin)).renomme(str(cible))

    fils = [threading.Thread(target=range_le_fichier, args=(c,)) for c in contenus]
    for fil in fils:
        fil.start()
    for fil in fils:
        fil.join(60)

    # Un seul nom cible possible : un seul fichier a pu être rangé…
    ranges = os.listdir(str(cible))
    assert ranges == [CIBLE], ranges
    # …et l'autre est **resté** : il n'a pas été supprimé au motif d'un
    # rangement qui n'a pas eu lieu.
    restes = sorted(str(source / nom) for nom in os.listdir(str(source)))
    assert len(restes) == 1, restes
    # Le fichier rangé est intact, et c'est bien celui qui a quitté l'entrée.
    (parti,) = set(contenus) - set(restes)
    assert (cible / CIBLE).read_bytes() == contenus[parti]
