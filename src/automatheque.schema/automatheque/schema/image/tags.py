# -*- coding: utf-8 -*-
"""Le vocabulaire des étiquettes d'une image.

`BaseTags` dit **ce qu'on sait** d'une photo — un album, une date de prise de
vue, des coordonnées, un appareil. Elle ne dit pas *où* c'est écrit, ni
comment l'y lire.

Le code d'origine mélangeait les deux : son adaptateur exiftool héritait de
cette classe, et écrire un attribut lançait un processus externe. Les deux
sont désormais séparés — un adaptateur sous-classe `BaseTags` et surcharge
`charge()`, mais il vit chez qui a besoin d'exiftool, pas ici.
"""

from datetime import datetime
from typing import Optional, Tuple

import attr


@attr.s
class BaseTags:
    """Les étiquettes d'une image, sans rien savoir de leur stockage.

    Les étiquettes ne **portent pas** le chemin du fichier décrit : ce serait
    une troisième vérité (après `Media.source`), qui divergerait après un
    renommage. La source est **reçue** au moment du chargement — `charge(source)`
    — et jamais mémorisée ici.
    """

    # Extensions reconnues, à déclarer par les familles qui spécialisent.
    extensions: Tuple[str, ...] = ()

    # Attributs qu'un adaptateur est censé charger. Une famille qui n'utilise
    # pas toute la liste (les vidéos, par exemple) n'en remonte qu'une partie.
    ATTRIBUTS_CHARGES = (
        "album",
        "evenement",
        "auteur",
        "date_prise_de_vue",
        "date_creation_fichier",
        "date_modification_fichier",
        "latitude",
        "longitude",
        "timezone",
        "pays",
        "province_etat",
        "ville",
        "lieu_quartier",
        "fabriquant_appareil",
        "modele_appareil",
        "nom_origine",
        "titre",
        "description",
        "evaluation",
    )

    # Un fuseau s'écrit « Europe/Paris », or « / » n'a pas sa place dans un nom
    # de fichier. Ce séparateur le remplace quand le fuseau transite par un
    # chemin, dans un sens comme dans l'autre.
    TIMEZONE_SEPARATEUR = "%"

    # Quoi, et de qui :
    album: Optional[str] = attr.ib(default=None, kw_only=True)
    evenement: Optional[object] = attr.ib(default=None, kw_only=True)
    auteur: Optional[str] = attr.ib(default=None, kw_only=True)
    titre: Optional[str] = attr.ib(default=None, kw_only=True)
    description: Optional[str] = attr.ib(default=None, kw_only=True)
    evaluation: Optional[int] = attr.ib(default=None, kw_only=True)
    nom_origine: Optional[str] = attr.ib(default=None, kw_only=True)

    # Quand :
    date_prise_de_vue: Optional[datetime] = attr.ib(default=None, kw_only=True)
    date_creation_fichier: Optional[datetime] = attr.ib(default=None, kw_only=True)
    date_modification_fichier: Optional[datetime] = attr.ib(default=None, kw_only=True)
    # Les dates des fichiers ne sont pas toujours lisibles avec leur fuseau ;
    # on le stocke donc à part plutôt que de le deviner. Cf.
    # TIMEZONE_SEPARATEUR pour son écriture dans un chemin.
    timezone: Optional[str] = attr.ib(default=None, kw_only=True)

    # Où :
    coordonnees_gps: Optional[object] = attr.ib(default=None, kw_only=True)
    latitude: Optional[float] = attr.ib(default=None, kw_only=True)
    longitude: Optional[float] = attr.ib(default=None, kw_only=True)
    lieu_quartier: Optional[str] = attr.ib(default=None, kw_only=True)
    ville: Optional[str] = attr.ib(default=None, kw_only=True)
    province_etat: Optional[str] = attr.ib(default=None, kw_only=True)
    pays: Optional[str] = attr.ib(default=None, kw_only=True)

    # Avec quoi :
    fabriquant_appareil: Optional[str] = attr.ib(default=None, kw_only=True)
    modele_appareil: Optional[str] = attr.ib(default=None, kw_only=True)

    def charge(self, source: Optional[str] = None) -> "BaseTags":
        """Remplit les étiquettes depuis ``source``. À surcharger.

        La source (le chemin du fichier décrit) est **reçue** à l'appel — elle
        n'est pas mémorisée par la classe, pour ne pas devenir une vérité qui se
        périme après un renommage. Un adaptateur — exiftool, un fichier
        « sidecar », une base — surcharge cette méthode, lit/écrit à côté de
        ``source``, et renvoie ``self``.

        Ici, il n'y a rien à charger : la classe ne sait pas d'où viendraient
        les valeurs. ``source`` est donc ignorée.
        """
        return self
