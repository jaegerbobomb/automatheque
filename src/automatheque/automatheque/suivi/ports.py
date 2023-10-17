import abc


class StockageAbstraite(abc.ABC):
    @abc.abstractmethod
    def existe(self, reference: str) -> bool:
        raise NotImplementedError

    @abc.abstractmethod
    def sauvegarde(self, reference: str, contenu: str) -> bool:
        raise NotImplementedError
