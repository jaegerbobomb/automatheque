#!/usr/bin/python
# -*- coding: utf-8 -*-
"""Utilitaires de manipulation des répertoires

Divers utilitaires.
"""

import os
from pathlib import Path
import errno


from automatheque.log import recup_logger

LOGGER = recup_logger(__name__)


def mkdir_p(path):
    """Crée un répertoire et son arborescence : équivalent à  "mkdir -p".

    Renvoie une erreur si la cible existe et n'est pas un répertoire.

    TODO déprécier pour Path.mkdir()
    """
    try:
        os.makedirs(path)
    except OSError as exc:  # Python >2.5
        if exc.errno == errno.EEXIST and os.path.isdir(path):
            pass
        else:
            raise


# Fonction supplémentaire à ajouter :
# TODO https://peterlyons.com/problog/2009/04/zip-dir-python


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
