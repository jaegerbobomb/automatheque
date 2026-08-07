# -*- coding: utf-8 -*-
"""Photo : une image et ses étiquettes.

La classe est réduite au vocabulaire — les extensions reconnues, les
étiquettes, le contrôle de validité. Elle ne sait ni se renommer, ni se
décomposer : ces comportements sont apportés par sous-classage, comme
`schema` le demande.

```py
from automatheque.decomposition import Decomposable
from automatheque.renommage import Renommable
from automatheque.schema.image import Photo


class PhotoRangeable(Photo, Renommable, Decomposable):
    ...
```
"""

import os
from typing import Optional

import attr

from automatheque.schema.media import Media

from .tags import BaseTags


@attr.s
class Photo(Media):
    """Une photo : un fichier image, et ce qu'on sait de lui.

    :param source: chemin complet vers le fichier
    :param tags: étiquettes de l'image ; par défaut des `BaseTags` vides,
                 rattachées à la même source. Un adaptateur (exiftool, fichier
                 « sidecar »…) se substitue à elles en passant sa propre
                 sous-classe de `BaseTags`.
    """

    # Extensions valides pour les photos. TODO que ça ?
    extensions = ("arw", "cr2", "dng", "gif", "jpeg", "jpg", "nef", "rw2")

    tags: BaseTags = attr.ib(
        default=attr.Factory(lambda self: BaseTags(source=self.source), takes_self=True)
    )

    @property
    def basename(self) -> Optional[str]:
        """Nom du fichier, sans son répertoire."""
        if self.source is None:
            return None
        return os.path.basename(self.source)

    def charge_tags(self) -> BaseTags:
        """Demande aux étiquettes de se remplir, et les renvoie.

        Sans adaptateur, c'est un aller-retour sans effet : `BaseTags.charge()`
        ne sait pas d'où viendraient les valeurs.
        """
        self.tags = self.tags.charge()
        return self.tags
