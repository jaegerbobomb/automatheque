# -*- coding: utf-8 -*-
"""Composition documentée `Photo` + `Renommable` + `Decomposable` (#117).

Test **inter-paquets** : il vérifie qu'après un rangement, *tous* les accès au
fichier suivent la cible — pas seulement celui qui a été mis à jour. C'est ce
qui empêche la divergence de revenir. Ignoré si `schema`/`decomposition` ne sont
pas installés (exécution isolée du seul paquet `renommage`).
"""

import os

import attr
import pytest

pytest.importorskip("automatheque.schema.image")
pytest.importorskip("automatheque.decomposition")

from automatheque.decomposition import Decomposable  # noqa: E402
from automatheque.renommage import Gabarit, Gabarits, Renommable  # noqa: E402
from automatheque.schema.image import BaseTags, Photo  # noqa: E402


@attr.s
class PhotoRangeable(Photo, Renommable, Decomposable):
    """La composition recommandée par le docstring de `Photo`."""

    @classmethod
    def _gabarits_par_defaut(cls):
        return Gabarits([Gabarit(squelette="{nom}.jpg", ordre=1)])

    def _liste_champs_dispo(self):
        return {"nom": "photo-rangee"}


@attr.s
class TagsSidecar(BaseTags):
    """Adaptateur « sidecar » minimal : il retient la source qu'on lui passe.

    Représente le cas de photomas : un adaptateur qui écrit **à côté** du media
    et a donc besoin de la source **à jour**.
    """

    source_vue = attr.ib(default=None, kw_only=True)

    def charge(self, source=None):
        self.source_vue = source
        return self


def test_composition_documentee_ne_diverge_pas_apres_rangement(tmp_path):
    src = tmp_path / "IMG_1234.jpg"
    src.write_bytes(b"\xff\xd8\xff\xe0" + b"x" * 200)

    p = PhotoRangeable(source=str(src))
    p.tags = TagsSidecar()

    cible = p.renomme(str(tmp_path / "range"))

    # Le fichier a bougé, l'original a disparu.
    assert os.path.exists(cible)
    assert not os.path.exists(str(src))

    # TOUS les accès pointent la cible, pas seulement celui qui a été écrit.
    assert p.source == cible
    assert p.basename == os.path.basename(cible)  # dérive de source
    # ce que `Decomposable` analyse par défaut suit aussi (redécomposer ne relit
    # plus l'ancien nom).
    assert p._prepare_decomposition() == os.path.basename(cible)

    # Les étiquettes voient la source **à jour** : un « sidecar » n'écrira pas à
    # côté de l'ancien emplacement.
    p.charge_tags()
    assert p.tags.source_vue == cible


def test_source_absente_refuse_le_rangement_clairement(tmp_path):
    """Sans `source`, on refuse tôt et clairement plutôt qu'un `shutil.copy`
    obscur au fond de la pile."""
    p = PhotoRangeable()  # source=None par défaut (Media)
    with pytest.raises(ValueError, match="source"):
        p.renomme(str(tmp_path / "range"))
