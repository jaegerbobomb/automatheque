import attr

from automatheque.suivi.adaptateurs.repertoire import StockageRepertoire
from automatheque.suivi.ports import StockageAbstraite


@attr.s
class JournalSuivi:
    """Journal de suivi d'une action quelconque.

    Exemple:

    >>> from pathlib import Path
    >>> from automatheque.suivi.journal import JournalSuivi, StockageRepertoire

    >>> stockage = StockageRepertoire(Path("/chemin/vers/stockage/suivi"))
    >>> journal = JournalSuivi(stockage)

    >>> if not journal.deja_fait(identifiant_unique_action):
    >>>     action_quelconque()
    >>>     journal.coche(identifiant_unique_action, contenu)
    """

    stockage: StockageAbstraite = attr.ib(default=StockageRepertoire())  # handler ?

    def deja_fait(self, reference: str) -> bool:
        return self.stockage.existe(reference)

    # decorator !!
    def ni_fait_ni_à_refaire(self, nom_arg_reference: str):
        """Décore une fonction pour qu'elle ne soit jouée qu'une fois pour un argument donné.

        Il faut donner en entrée le nom du paramètre qui contient la référence, et la
        decoration sauvegardera "nom_fonction_reference".

        TODO ajouter option pour date.
        """
        pass

    def coche(self, reference: str, contenu: str) -> bool:
        return self.stockage.sauvegarde(reference, contenu)
