#!/usr/bin/python
# -*- coding: utf-8 -*-
"""Décorateur de réessais avec attente croissante.

Besoin récurrent des scripts qui parlent au réseau : réessayer une opération
instable en patientant de plus en plus longtemps entre les tentatives.

Exemple ::

    @reessaye(tentatives=4, delai=2, multiplicateur=2, exceptions=(ConnectionError,))
    def appel_api():
        ...

Avec ces paramètres, ``appel_api`` est tentée jusqu'à 4 fois, avec des pauses
de 2s, 4s puis 8s entre les essais. Si les 4 essais échouent, la dernière
exception est relevée telle quelle.
"""

import functools
import logging
from random import uniform
from time import sleep

LOGGER = logging.getLogger(__name__)


def reessaye(tentatives=4, delai=2, multiplicateur=2, exceptions=(Exception,), gigue=0):
    """Décore une fonction pour la réessayer lorsqu'elle lève une exception.

    :param tentatives: nombre total d'essais (>= 1). Si tous échouent, la
        dernière exception rencontrée est relevée.
    :param delai: délai initial en secondes avant le premier réessai.
    :param multiplicateur: facteur appliqué au délai après chaque échec
        (l'attente croît donc géométriquement).
    :param exceptions: type d'exception, ou tuple de types, qui déclenche un
        réessai. Toute autre exception est propagée immédiatement, sans réessai.
    :param gigue: ajout aléatoire maximal (en secondes) à chaque délai, pour
        désynchroniser des réessais simultanés. ``0`` (défaut) la désactive.
    :raise ValueError: si ``tentatives`` < 1, ou si ``delai`` /
        ``multiplicateur`` / ``gigue`` sont négatifs.
    """
    if tentatives < 1:
        raise ValueError("tentatives doit être >= 1")
    if delai < 0 or multiplicateur < 0 or gigue < 0:
        raise ValueError("delai, multiplicateur et gigue doivent être positifs")
    if not isinstance(exceptions, tuple):
        exceptions = (exceptions,)

    def decorateur(fonction):
        # `functools.partial` et autres callables n'ont pas toujours __name__.
        nom = getattr(fonction, "__name__", repr(fonction))

        @functools.wraps(fonction)
        def enveloppe(*args, **kwargs):
            attente = delai
            for essai in range(1, tentatives + 1):
                try:
                    return fonction(*args, **kwargs)
                except exceptions as exc:
                    # Dernier essai : on ne patiente plus, on relève l'erreur.
                    if essai >= tentatives:
                        LOGGER.warning(
                            "{} a échoué après {} tentative(s) : {}".format(
                                nom, tentatives, exc
                            )
                        )
                        raise
                    pause = attente + (uniform(0, gigue) if gigue else 0)
                    LOGGER.debug(
                        "{} a échoué (essai {}/{}) : {}. "
                        "Nouvel essai dans {:.2f}s".format(
                            nom, essai, tentatives, exc, pause
                        )
                    )
                    sleep(pause)
                    attente *= multiplicateur

        return enveloppe

    return decorateur
