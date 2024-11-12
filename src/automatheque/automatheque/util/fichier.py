# -*- coding: utf-8 -*-
"""Utilitaires de manipulation des fichiers."""


def enleve_caracteres_invalides(value):
    """Supprime les caractères incompatibles avec le système de fichier.

    https://stackoverflow.com/questions/1033424/how-to-remove-bad-path-characters-in-python
    """
    deletechars = '/\:*?"<>|'
    # TODO tester la plateforme
    deletechars = "/"  # Linux autorise quasiment tout le reste
    try:
        for c in deletechars:
            value = value.replace(c, "_")
    except Exception:
        # si la valeur est un int ou autre, on la renvoie telle quelle
        pass
    return value
