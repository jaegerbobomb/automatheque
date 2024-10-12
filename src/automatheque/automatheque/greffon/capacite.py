from typing import Protocol


class Capacite(Protocol):
    """Représente le Protocol exigé pour une capacité donnée.

    Chaque Greffon doit "implémenter cette interface", s'il indique qu'il
    répond à cette Capacité via sa liste Greffon.CAPACITES.

    .. code-block:: python

       class LireCapacite(Capacite, Protocol):
           # Protocol à respecter
           def lire(self) -> bool:
               ...

       class LecteurGreffon(Greffon):
           CAPACITES = [LireCapacite]
           def lire(self) -> bool:
               # implémente le Protocol LireCapacite
               pass

       greffons : List[LireCapacite] = Greffon.greffons_par_capacite(LireCapacite)
       greffons[O].lire()
    """

    pass
