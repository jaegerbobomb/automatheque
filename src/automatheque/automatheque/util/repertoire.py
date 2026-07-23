#!/usr/bin/python
# -*- coding: utf-8 -*-
"""Utilitaires de manipulation des répertoires

Divers utilitaires.
"""

import errno
import logging
import os
import warnings
from pathlib import Path

LOGGER = logging.getLogger(__name__)


def mkdir_p(path):
    """Crée un répertoire et son arborescence : équivalent à  "mkdir -p".

    Renvoie une erreur si la cible existe et n'est pas un répertoire.

    .. deprecated::
        Utiliser directement :meth:`pathlib.Path.mkdir` ::

            Path(path).mkdir(parents=True, exist_ok=True)

        Ce raccourci maison n'apporte plus rien face à ``pathlib`` (Python 3) et
        sera retiré dans une version ultérieure. Cf. #24.
    """
    warnings.warn(
        "mkdir_p est déprécié : utilisez "
        "Path(path).mkdir(parents=True, exist_ok=True).",
        DeprecationWarning,
        stacklevel=2,
    )
    # Comportement conservé : crée l'arborescence, ne lève pas si le répertoire
    # existe déjà, mais lève si la cible est un fichier existant
    # (``FileExistsError``, sous-classe d'``OSError``).
    Path(path).mkdir(parents=True, exist_ok=True)


def supprime(repertoire, force=False):
    """Supprime un répertoire s'il est vide."""
    try:
        os.rmdir(repertoire)
        LOGGER.debug("Repertoire {} supprime car vide".format(repertoire))
    except OSError as ex:
        if ex.errno == errno.ENOTEMPTY and not force:
            LOGGER.warning("Repertoire {} non supprime car non vide".format(repertoire))


def remonte_arborescence(fichier, racine=None):
    """Générateur qui renvoie le niveau précédent de l'arborescence.

    Il s'arrête une fois que la racine est trouvée.

    :raise: ValueError si fichier n'est pas rattaché à la racine donnée
    """
    if not isinstance(fichier, Path):
        fichier = Path(fichier)
    racine = fichier.root if not racine else racine
    if not isinstance(racine, Path):
        racine = Path(racine)

    if fichier.relative_to(racine):
        parents_relatifs = [i for i in fichier.parents if i not in racine.parents]
        for parent in parents_relatifs[:-1]:
            yield parent


def iter_fichiers(source):
    """Itérateur de la liste des fichiers d'une source Path.

    On crée un itérateur que l'on ait reçu un fichier ou un rep en entrée !

    :param source: Source des fichiers : 1 rep ou 1 fichier
    :type source: Path
    """
    if source.is_dir():
        # On récupère tous les fichiers récursivement :
        fichiers = source.rglob("*")
    else:
        # On ne récupère que le fichier d'entrée :
        fichiers = source.parent.glob(source.name)
    return [f for f in fichiers if not f.is_dir()]
