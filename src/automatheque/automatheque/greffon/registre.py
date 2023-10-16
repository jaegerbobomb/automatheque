from typing import TYPE_CHECKING, Union

from automatheque.conception.structures import MetaInstancePersistanteRegistre

if TYPE_CHECKING:
    from automatheque.greffon.greffon import Greffon


class RegistreGreffons(metaclass=MetaInstancePersistanteRegistre):
    """
    Stocke toutes les instances des greffons qui héritent de `~automatheque.greffon.Greffon`.

    Fournit plusieurs méthodes de classe pour récupérer les Greffons par nom ou par capacité.
    """

    @classmethod
    def greffons_par_capacite(cls, capacite: str):
        return [
            p for p in cls._instances(inclure_enfants=True) if capacite in p.capacites
        ]

    @classmethod
    def greffons_identifiants(cls):
        return [p.identifiant for p in cls._instances(inclure_enfants=True)]

    @classmethod
    def greffon_par_identifiant(cls, identifiant: str) -> Union[Greffon, None]:
        greffons = [
            p
            for p in cls._instances(inclure_enfants=True)
            if p.identifiant == identifiant
        ]
        return greffons[0] if greffons else None
