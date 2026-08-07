# -*- coding: utf-8 -*-
"""Emplacement : relie une position GPS et une adresse.

Le passage de la position GPS à l'adresse et vice versa s'appelle en anglais
le *geocoding* (et *nominatim*). Ce module n'en fait rien : il ne porte que le
vocabulaire. Interroger un service de géocodage est l'affaire d'un
connecteur — par exemple `localisation_gps`.
"""

from math import cos, radians, sqrt
from typing import Optional, Tuple

import attr


@attr.s
class Emplacement:
    """Un lieu, décrit par ses coordonnées, son adresse, ou les deux.

    Les composantes de l'adresse (`rue`, `ville`, `pays`…) sont facultatives :
    elles sont remplies par un géocodage inverse quand il y en a un.
    """

    # `None` — et non `0` — pour « pas de coordonnée » : zéro est une latitude
    # et une longitude parfaitement valides (l'équateur, le méridien de
    # Greenwich), qu'on ne peut pas distinguer d'une absence si on les
    # confond.
    latitude: Optional[float] = attr.ib(
        default=None, converter=attr.converters.optional(float)
    )
    longitude: Optional[float] = attr.ib(
        default=None, converter=attr.converters.optional(float)
    )
    adresse: str = attr.ib(default="")

    precision: str = attr.ib(kw_only=True, default="")
    qualite: str = attr.ib(kw_only=True, default="")
    numero_adresse: str = attr.ib(kw_only=True, default="")
    rue: str = attr.ib(kw_only=True, default="")
    ville: str = attr.ib(kw_only=True, default="")
    etat: str = attr.ib(kw_only=True, default="")
    pays: str = attr.ib(kw_only=True, default="")
    code_postal: str = attr.ib(kw_only=True, default="")

    # Attribut supplémentaire pour stocker un nom personnalisé, par ex :
    # "Maison" ou "Bureau" etc. que l'on pourra remplir à la main ou à partir
    # des contacts ou autre.
    nom_personnalise: str = attr.ib(kw_only=True, default="")

    def valide(self) -> bool:
        """Renvoie si l'emplacement est valide ou non.

        Un emplacement vaut par ses coordonnées **ou** par son adresse : l'un
        des deux suffit à le situer.

        Le test porte sur la **présence** des coordonnées, pas sur leur
        valeur : un point sur l'équateur ou sur le méridien de Greenwich a une
        coordonnée nulle et n'en est pas moins situé.
        """
        a_des_coordonnees = self.latitude is not None and self.longitude is not None
        return a_des_coordonnees or bool(self.adresse)

    @staticmethod
    def decimal_en_dms(decimal) -> Tuple[float, float, float, int]:
        """Convertit des degrés décimaux en degrés / minutes / secondes.

        :param decimal: angle en degrés décimaux (ex: -38.2410611)
        :returns: tuple `(degrés, minutes, secondes, signe)`, le signe valant
                  1 ou -1 — les trois premières valeurs sont **absolues**
        """
        decimal = float(decimal)
        decimal_abs = abs(decimal)
        minutes, secondes = divmod(decimal_abs * 3600, 60)
        degres, minutes = divmod(minutes, 60)
        signe = 1 if decimal >= 0 else -1
        return (degres, minutes, secondes, signe)

    @staticmethod
    def dms_en_decimal(degres, minutes, secondes, direction=" ") -> float:
        """Convertit des degrés / minutes / secondes en degrés décimaux.

        :param direction: point cardinal ; `W` et `S` donnent un angle négatif
        """
        signe = -1 if direction and direction[0] in "WSws" else 1
        return (
            float(degres) + (float(minutes) / 60) + (float(secondes) / 3600)
        ) * signe

    @staticmethod
    def dms_en_chaine(decimal, axe: str = "latitude") -> str:
        """Formate des degrés décimaux à la façon d'exiftool.

        Exemple de sortie : ``38 deg 14' 27.82" S``.

        :param axe: `latitude` ou `longitude`, qui décide du point cardinal
        """
        degres, minutes, secondes, _signe = Emplacement.decimal_en_dms(decimal)
        if axe == "latitude":
            direction = "N" if float(decimal) >= 0 else "S"
        elif axe == "longitude":
            direction = "E" if float(decimal) >= 0 else "W"
        else:
            raise ValueError("axe doit valoir 'latitude' ou 'longitude'")
        # `decimal_en_dms` rend des flottants (divmod sur flottants) : degrés et
        # minutes sont entiers par nature, les secondes s'arrondissent — sinon on
        # obtient « 38.0 deg 14.0' 27.8199…" » au lieu du format exiftool.
        return "{} deg {}' {}\" {}".format(
            int(degres), int(minutes), round(secondes, 2), direction
        )

    def distance(self, lat, lon) -> float:
        """Renvoie une distance approximative, en mètres, avec une autre paire.

        Cette distance n'est valable que pour des points proches. Ne pas
        l'utiliser pour des calculs précis ou des points éloignés.

        Récupéré de https://github.com/jmathai/elodie (`localstorage.py`) et
        http://stackoverflow.com/questions/15736995.

        :param lat: latitude du point à mesurer
        :param lon: longitude du point à mesurer
        :raise ValueError: si cet emplacement n'a pas de coordonnées
        """
        if self.latitude is None or self.longitude is None:
            raise ValueError(
                "Emplacement sans coordonnées : distance incalculable "
                "(latitude={!r}, longitude={!r})".format(self.latitude, self.longitude)
            )
        # Conversion degrés "décimaux" en radians
        lon1, lat1, lon2, lat2 = list(
            map(radians, [lon, lat, self.longitude, self.latitude])
        )

        r = 6371000  # rayon de la Terre, en mètres
        x = (lon2 - lon1) * cos(0.5 * (lat2 + lat1))
        y = lat2 - lat1
        return r * sqrt(x * x + y * y)
