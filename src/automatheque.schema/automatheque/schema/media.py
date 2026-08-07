# -*- coding: utf-8 -*-
"""Media : ce qui est commun aux familles `image`, `video`, `audio`, `texte`.

Un média, ici, c'est un fichier et ce qu'on peut dire de lui **sans
l'ouvrir** : son chemin, son extension, son type MIME deviné. La classe ne
lit rien sur le disque — reconnaître un contenu réel est l'affaire d'un
adaptateur.
"""

import mimetypes
import os
from typing import Optional, Tuple

import attr


@attr.s
class Media:
    """Classe de base pour tous les médias.

    Les familles la spécialisent en déclarant leurs `extensions` :

    ```py
    @attr.s
    class Photo(Media):
        extensions = ("jpg", "png")
    ```

    :param source: chemin complet vers le fichier
    """

    # Extensions reconnues par la famille. Vide ici : `valide()` d'un `Media`
    # nu est donc toujours faux, ce qui est la bonne réponse — on ne sait pas
    # de quelle famille il relève.
    extensions: Tuple[str, ...] = ()

    source: Optional[str] = attr.ib(default=None)
    # Empreinte du contenu, calculée par qui sait le faire (déduplication,
    # recherche de similaires). Jamais remplie ici : la calculer réclame de
    # lire le fichier.
    empreinte: Optional[str] = attr.ib(init=False, default=None)

    @property
    def extension(self) -> str:
        """Extension du fichier, en minuscules et sans le point."""
        return os.path.splitext(self.source)[1][1:].lower()

    @property
    def mimetype(self) -> Optional[str]:
        """Type MIME **deviné d'après le nom**, ou None s'il est inconnu.

        Deviné, pas constaté : `mimetypes` lit l'extension, pas le contenu.
        """
        return mimetypes.guess_type(self.source)[0]

    def valide(self) -> bool:
        """Renvoie si l'extension du fichier est reconnue par la famille.

        C'est un contrôle de **nom**, pas de contenu.
        """
        return self.extension in self.extensions
