# -*- coding: utf-8 -*-
"""Vidéos : films, séries et épisodes.

Réduit au vocabulaire — ce qu'on sait d'une vidéo, sans rien lire ni nettoyer.
Reconnaître un épisode dans un nom de fichier, choisir l'arborescence de
rangement, interroger un service en ligne : autant de comportements apportés
par sous-classage ou par des adaptateurs, comme `schema` le demande.

```py
from automatheque.decomposition import Decomposable
from automatheque.renommage import Renommable
from automatheque.schema.video import Episode


class EpisodeRangeable(Episode, Renommable, Decomposable):
    ...
```
"""

import os
from datetime import date
from typing import Dict, Iterable, Optional, Tuple, Union

import attr

from automatheque.schema.media import Media

IdExterne = Union[str, int]


def _ids(valeurs: Optional[Dict[str, IdExterne]]) -> Dict[str, str]:
    """Ids externes `{service: id}`, en chaînes quel que soit l'adaptateur."""
    return {str(service): str(id_) for service, id_ in (valeurs or {}).items()}


def _numeros(valeurs: Iterable[Union[int, str]]) -> Tuple[int, ...]:
    """Numéros d'épisode : un ensemble, rendu trié."""
    return tuple(sorted({int(v) for v in valeurs}))


@attr.s
class Serie:
    """Une série : ce qui est commun à ses épisodes.

    Ce n'est pas un `Media` : une série n'est pas un fichier.

    :param ids: identifiants chez des services externes, `{"tvdb": "81189"}`
    """

    titre: Optional[str] = attr.ib(default=None, kw_only=True)
    annee: Optional[int] = attr.ib(default=None, kw_only=True)
    ids: Dict[str, str] = attr.ib(factory=dict, converter=_ids, kw_only=True)


@attr.s
class Video(Media):
    """Socle des vidéos : un fichier vidéo et ses identifiants externes.

    :param source: chemin complet vers le fichier
    :param ids: identifiants chez des services externes, `{"imdb": "tt…"}`
    """

    extensions = ("avi", "m4v", "mkv", "mov", "mp4", "mpeg", "mpg", "ts", "webm", "wmv")

    ids: Dict[str, str] = attr.ib(factory=dict, converter=_ids, kw_only=True)

    @property
    def basename(self) -> Optional[str]:
        """Nom du fichier, sans son répertoire."""
        if self.source is None:
            return None
        return os.path.basename(self.source)


@attr.s
class Film(Video):
    """Un film."""

    titre: Optional[str] = attr.ib(default=None, kw_only=True)
    annee: Optional[int] = attr.ib(default=None, kw_only=True)


@attr.s
class Episode(Video):
    """Un ou plusieurs épisodes d'une série, contenus dans un même fichier.

    :param numeros: numéros des épisodes du fichier — plusieurs pour un
                    fichier double (`S01E01E02`), rendus triés et sans doublon
    :param titre: titre de l'épisode, s'il est connu
    """

    serie: Serie = attr.ib(factory=Serie, kw_only=True)
    saison: Optional[int] = attr.ib(default=None, kw_only=True)
    numeros: Tuple[int, ...] = attr.ib(default=(), converter=_numeros, kw_only=True)
    titre: Optional[str] = attr.ib(default=None, kw_only=True)
    description: Optional[str] = attr.ib(default=None, kw_only=True)
    date_diffusion: Optional[date] = attr.ib(default=None, kw_only=True)
