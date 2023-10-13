from pathlib import Path

import attr

from ..suivi import StockageAbstraite

# journal_suivi.adaptateur.StockageRepertoire
@attr.s
class StockageRepertoire(StockageAbstraite):
    repertoire: Path = attr.ib(default=Path("/"))

    def __attr_post_init__(self):
        # TODO >= py3.5
        self.repertoire.mkdir(parents=True, exist_ok=True)

    def existe(self, reference: str):
        # TODO mutex pour thread safety
        fichier = self.repertoire / reference
        return fichier.exists()

    def sauvegarde(self, reference: str, contenu: str):
        fichier = self.repertoire / reference
        with open(fichier, "w") as f:
            f.write(contenu)
        return True
