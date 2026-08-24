# -*- coding: utf-8 -*-
"""Value object ``Montant`` : une valeur exacte (``Decimal``) et sa devise.

Pensé pour l'argent, où le ``float`` est proscrit (arrondis binaires) et où
mélanger des devises est une **erreur**, pas une conversion silencieuse. La
présentation et la saisie localisées (séparateurs, symbole) sont **découplées**
du modèle : elles passent par un :class:`FormatMonetaire` paramétrable — le
français n'est qu'un préréglage parmi d'autres, pas une valeur figée (même
principe que la locale des durées, #136).

Le change de devise est possible mais **reçoit** son taux (schema est une
feuille du graphe : il ne connaît aucune source de taux, ne va rien chercher).
"""

import re
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation
from typing import Optional, Union

import attr


class MontantInvalide(ValueError):
    """Le texte ou la valeur ne représente pas un montant exact."""


class DevisesIncompatibles(ValueError):
    """Opération entre deux montants de devises différentes."""


def _vers_decimal(valeur: Union[Decimal, int, str]) -> Decimal:
    """Ramène une valeur à un ``Decimal`` exact ; refuse le ``float``."""
    if isinstance(valeur, Decimal):
        return valeur
    if isinstance(valeur, float):
        # Decimal(0.1) exposerait le bruit binaire du float : la valeur exacte
        # doit venir d'un texte, d'un entier ou d'un Decimal.
        raise MontantInvalide(
            f"float refusé ({valeur!r}) : passez un Decimal, un entier ou un "
            "texte (Montant.depuis_texte pour les écritures localisées)"
        )
    try:
        return Decimal(valeur)
    except InvalidOperation as erreur:
        raise MontantInvalide(f"montant illisible : {valeur!r}") from erreur


@attr.s(frozen=True)
class FormatMonetaire:
    """Locale d'écriture d'un montant : séparateurs, symbole, position.

    Découple la *présentation/saisie* du modèle. Deux préréglages sont fournis
    (:data:`FR`, :data:`US`) ; tout autre style se décrit en instanciant.
    """

    separateur_decimal: str = attr.ib(default=",")
    separateur_milliers: str = attr.ib(default=" ")  # espace fine insécable
    symbole: str = attr.ib(default="€")
    symbole_avant: bool = attr.ib(default=False)
    espace_symbole: str = attr.ib(default=" ")  # insécable


#: Écriture française : ``1 234,56 €`` (espace fine insécable, symbole après).
FR = FormatMonetaire()

#: Écriture anglo-américaine : ``$1,234.56`` (symbole avant, sans espace).
US = FormatMonetaire(
    separateur_decimal=".",
    separateur_milliers=",",
    symbole="$",
    symbole_avant=True,
    espace_symbole="",
)


# order=False : attrs générerait des comparaisons de tuples (valeur, devise) qui
# écraseraient les nôtres — or comparer deux devises différentes doit LEVER, pas
# ordonner par nom de devise.
@attr.s(frozen=True, order=False)
class Montant:
    """Un montant exact dans une devise.

    >>> Montant.depuis_texte("1 234,56") + Montant.depuis_texte("0,44")
    Montant(valeur=Decimal('1235.00'), devise='EUR')
    """

    valeur: Decimal = attr.ib(converter=_vers_decimal)
    devise: str = attr.ib(default="EUR", converter=lambda d: str(d).upper())

    @devise.validator
    def _devise_non_vide(self, attribut, valeur):
        if not valeur:
            raise MontantInvalide("devise vide")

    @classmethod
    def depuis_texte(
        cls, texte: str, devise: str = "EUR", *, fmt: Optional[FormatMonetaire] = None
    ) -> "Montant":
        """Parse une écriture localisée en montant exact.

        Sans ``fmt``, la désambiguïsation est **structurelle** (elle absorbe
        les écritures usuelles des relevés, quelle que soit la locale) : si
        l'écriture se termine par un point décimal (``10,500.00``), les virgules
        sont des séparateurs de milliers ; sinon la virgule est décimale
        (``10 500,00``). Les espaces, symboles et lettres sont ignorés.

        Avec un ``fmt`` explicite, la lecture est **déterministe** pour cette
        locale — c'est ainsi qu'on lève l'ambiguïté d'un ``"1,234"`` : il vaut
        ``1234`` avec ``fmt=US``, ``1.234`` avec ``fmt=FR``.
        """
        if fmt is not None:
            nettoye = re.sub(r"[^\d,.\-+]", "", texte).replace(
                fmt.separateur_milliers, ""
            )
            nettoye = nettoye.replace(fmt.separateur_decimal, ".")
        else:
            # Ne garde que chiffres, séparateurs et signe (symboles/espaces —
            # insécables comprises — et lettres tombent).
            nettoye = re.sub(r"[^\d,.\-+]", "", texte.strip())
            if re.match(r"^[-+]?[\d,]+\.\d+$", nettoye):
                nettoye = nettoye.replace(",", "")  # virgules = milliers
            nettoye = nettoye.replace(",", ".")  # virgule restante = décimale
        return cls(_vers_decimal(nettoye), devise)

    def _meme_devise(self, autre: "Montant") -> None:
        if self.devise != autre.devise:
            raise DevisesIncompatibles(
                f"{self.devise} et {autre.devise} : convertir explicitement "
                "avant d'opérer"
            )

    def convertit(self, devise: str, taux: Union[Decimal, int]) -> "Montant":
        """Convertit vers ``devise`` au ``taux`` fourni.

        Le taux est **reçu**, jamais recherché : schema est une feuille du graphe
        et ne connaît aucune source de cours. À l'appelant de le fournir (depuis
        une API, une config…), en ``Decimal`` exact (le ``float`` est refusé).

        >>> Montant.depuis_texte("10,00").convertit("USD", Decimal("1.08")).valeur
        Decimal('10.8000')
        """
        return Montant(self.valeur * _vers_decimal(taux), devise)

    def arrondi(self, decimales: int = 2, mode: str = ROUND_HALF_UP) -> "Montant":
        """Arrondit la valeur à ``decimales`` chiffres (par défaut le centime).

        Utile après un :meth:`convertit` ou une multiplication, qui produisent
        des valeurs à précision arbitraire.
        """
        quantum = Decimal(1).scaleb(-decimales)
        return Montant(self.valeur.quantize(quantum, rounding=mode), self.devise)

    def __add__(self, autre: "Montant") -> "Montant":
        if not isinstance(autre, Montant):
            return NotImplemented
        self._meme_devise(autre)
        return Montant(self.valeur + autre.valeur, self.devise)

    def __sub__(self, autre: "Montant") -> "Montant":
        if not isinstance(autre, Montant):
            return NotImplemented
        self._meme_devise(autre)
        return Montant(self.valeur - autre.valeur, self.devise)

    def __neg__(self) -> "Montant":
        return Montant(-self.valeur, self.devise)

    def __mul__(self, facteur: Union[int, Decimal]) -> "Montant":
        if isinstance(facteur, float):
            raise MontantInvalide("float refusé : multipliez par un Decimal")
        if not isinstance(facteur, (int, Decimal)):
            return NotImplemented
        return Montant(self.valeur * facteur, self.devise)

    __rmul__ = __mul__

    def __lt__(self, autre: "Montant"):
        if not isinstance(autre, Montant):
            return NotImplemented
        self._meme_devise(autre)
        return self.valeur < autre.valeur

    def __le__(self, autre: "Montant"):
        if not isinstance(autre, Montant):
            return NotImplemented
        self._meme_devise(autre)
        return self.valeur <= autre.valeur

    def __gt__(self, autre: "Montant"):
        if not isinstance(autre, Montant):
            return NotImplemented
        self._meme_devise(autre)
        return self.valeur > autre.valeur

    def __ge__(self, autre: "Montant"):
        if not isinstance(autre, Montant):
            return NotImplemented
        self._meme_devise(autre)
        return self.valeur >= autre.valeur

    def __str__(self) -> str:
        return f"{self.valeur} {self.devise}"

    def texte(self, fmt: FormatMonetaire = FR) -> str:
        """Écriture localisée : ``1 234,56 €`` (FR), ``$1,234.56`` (US)…

        La valeur est présentée à deux décimales (arrondi d'affichage).
        """
        signe = "-" if self.valeur < 0 else ""
        entier, _, decimales = f"{abs(self.valeur):.2f}".partition(".")
        groupes = []
        while len(entier) > 3:
            groupes.insert(0, entier[-3:])
            entier = entier[:-3]
        groupes.insert(0, entier)
        corps = (
            signe
            + fmt.separateur_milliers.join(groupes)
            + fmt.separateur_decimal
            + decimales
        )
        if fmt.symbole_avant:
            return f"{fmt.symbole}{fmt.espace_symbole}{corps}"
        return f"{corps}{fmt.espace_symbole}{fmt.symbole}"
