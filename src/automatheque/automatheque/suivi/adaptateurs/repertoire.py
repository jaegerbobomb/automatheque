import threading
from pathlib import Path

import attr

from automatheque.suivi.ports import StockageAbstraite


@attr.s
class StockageRepertoire(StockageAbstraite):
    repertoire: Path = attr.ib(default=Path("/tmp"))
    # Sérialise les accès au système de fichiers pour rendre l'adaptateur
    # utilisable depuis plusieurs threads. Non passé à l'``__init__``, ni
    # comparé/affiché. Cf. #25.
    _verrou: threading.Lock = attr.ib(
        factory=threading.Lock, init=False, repr=False, eq=False
    )

    def __attrs_post_init__(self):
        self.repertoire.mkdir(parents=True, exist_ok=True)

    def existe(self, reference: str):
        fichier = self.repertoire / reference
        with self._verrou:
            return fichier.exists()

    def sauvegarde(self, reference: str, contenu: str):
        fichier = self.repertoire / reference
        with self._verrou:
            with open(fichier, "w") as f:
                f.write(contenu)
        return True
