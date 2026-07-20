# -*- coding: utf-8 -*-
"""Utilitaires de manipulation des fichiers."""

import os

# Caractères interdits dans un nom de fichier, par famille de plateforme.
# Sous Windows (``os.name == "nt"``) l'ensemble est bien plus large ; les
# systèmes POSIX (Linux, macOS) n'interdisent guère que le séparateur.
# Cf. #25.
CARACTERES_INVALIDES_NT = r'/\:*?"<>|'
CARACTERES_INVALIDES_POSIX = "/"


def enleve_caracteres_invalides(value):
    """Supprime les caractères incompatibles avec le système de fichier.

    L'ensemble des caractères retirés dépend de la plateforme courante
    (cf. ``os.name``).

    https://stackoverflow.com/questions/1033424/how-to-remove-bad-path-characters-in-python
    """
    deletechars = (
        CARACTERES_INVALIDES_NT if os.name == "nt" else CARACTERES_INVALIDES_POSIX
    )
    try:
        for c in deletechars:
            value = value.replace(c, "_")
    except Exception:
        # si la valeur est un int ou autre, on la renvoie telle quelle
        pass
    return value
