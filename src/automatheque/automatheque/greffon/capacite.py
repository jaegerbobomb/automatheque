from typing import List, Protocol, Type, Union

from automatheque.exceptions import CapaciteNonRendue


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

    Déclarer une capacité **engage** : la classe est vérifiée à sa définition
    (cf. :func:`verifie_capacites`). Une capacité peut aussi être une simple
    **chaîne** — une étiquette, qui n'exige donc aucun membre.
    """

    pass


#: Ce qu'un greffon peut déclarer dans ``CAPACITES`` : le **Protocol** d'une
#: capacité — la classe, pas une instance — ou la chaîne d'une étiquette.
TypeCapacite = Union[Type[Capacite], str]

#: Bases de la machinerie `typing` à ignorer quand on relève les membres d'une
#: capacité : elles n'appartiennent pas au contrat.
_BASES_TECHNIQUES = frozenset({"Protocol", "Generic", "object", "Capacite"})


def membres_capacite(capacite: TypeCapacite) -> List[str]:
    """Les membres publics qu'un greffon doit fournir pour rendre ``capacite``.

    Une capacité déclarée par une chaîne (étiquette) n'en exige aucun.
    """
    if not isinstance(capacite, type):
        return []
    membres: List[str] = []
    for base in capacite.__mro__:
        if base.__name__ in _BASES_TECHNIQUES:
            continue
        attributs = vars(base)
        noms = list(attributs) + list(attributs.get("__annotations__", {}))
        membres.extend(
            nom for nom in noms if not nom.startswith("_") and nom not in membres
        )
    return membres


def capacites_declarees(classe: type) -> List[TypeCapacite]:
    """Les capacités de ``classe``, **cumulées** sur tout son héritage.

    Une sous-classe **ajoute** ses capacités à celles de ses mères, au lieu de
    les masquer : ses propres déclarations viennent d'abord, puis celles
    héritées, sans doublon.
    """
    capacites: List[TypeCapacite] = []
    for base in classe.__mro__:
        for capacite in vars(base).get("CAPACITES", ()):
            if capacite not in capacites:
                capacites.append(capacite)
    return capacites


def verifie_capacites(classe: type) -> None:
    """Vérifie que ``classe`` rend les capacités qu'elle déclare.

    Annoncer une capacité sans l'implémenter ne se voyait qu'au point d'usage,
    chez l'appelant, sous la forme d'un ``AttributeError`` opaque — alors que
    c'est une erreur de code, visible dès la définition de la classe. Le membre
    peut être **hérité** : seul compte le fait que le greffon le fournisse.

    :raise CapaciteNonRendue: si un membre exigé par une capacité manque.
    """
    for capacite in capacites_declarees(classe):
        manquants = [
            membre
            for membre in membres_capacite(capacite)
            if not hasattr(classe, membre)
        ]
        if manquants:
            raise CapaciteNonRendue(classe, capacite, manquants)
