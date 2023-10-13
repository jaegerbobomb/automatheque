import abc

import attr

from .adaptateurs.repertoire import StockageRepertoire


class StockageAbstraite(abc.ABC):
    @abc.abstractmethod
    def existe(self, reference: str) -> bool:
        raise NotImplementedError

    @abc.abstractmethod
    def sauvegarde(self, reference: str, contenu: str) -> bool:
        raise NotImplementedError


@attr.s
class JournalSuivi:
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
        return self.stockage.enregistre(reference, contenu)
