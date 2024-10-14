from __future__ import annotations

from typing import TYPE_CHECKING, List, Optional, Type, TypeVar, Union

from automatheque.conception.structures import MetaInstancePersistanteRegistre
from automatheque.greffon.capacite import Capacite

if TYPE_CHECKING:
    from automatheque.greffon.greffon import Greffon


T = TypeVar("T", bound=Capacite)


class RegistreGreffons(metaclass=MetaInstancePersistanteRegistre):
    """
    Stocke toutes les instances des greffons qui héritent de `~automatheque.greffon.Greffon`.

    Fournit plusieurs méthodes de classe pour récupérer les Greffons par nom ou par capacité.
    """

    @classmethod
    def greffons_par_capacite(cls, capacite: Type[T]) -> List[Union[T, Greffon]]:
        """Les Greffons renvoyés sont censés respecter le Protocol "capacite" donné.

        TODO https://github.com/python/mypy/issues/4717 mypy ne gère pas correctement
             les Protocol ou classes abstraites passées en paramètre, donc
             Type[CapaciteProtocol] renvoie `Only concrete class can be given`.
             Pour l'instant il faut forcer le type en retour de l'appel :
             `greffons: CapaciteDemandeeProtocol = rg.greffons_par_capacite(CapaciteDemandeeProtocol)`

        :param capacite: Protocol que doit respecter le Greffon recherché
        :return: Union type, mais devrait être Intersect (TODO https://github.com/python/typing/issues/213)
        """
        return [
            p
            for p in cls._instances(inclure_enfants=True)
            if capacite.__class__ in [c.__class__ for c in p.capacites]
        ]

    @classmethod
    def greffons_identifiants(cls) -> List[str]:
        return [p.identifiant for p in cls._instances(inclure_enfants=True)]

    @classmethod
    def greffon_par_identifiant(cls, identifiant: str) -> Optional[Greffon]:
        greffons = [
            p
            for p in cls._instances(inclure_enfants=True)
            if p.identifiant == identifiant
        ]
        return greffons[0] if greffons else None
