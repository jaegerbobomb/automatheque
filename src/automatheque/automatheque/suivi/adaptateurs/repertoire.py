# -*- coding: utf-8 -*-
"""Shim de rétro-compatibilité : ``suivi.adaptateurs`` → ``suivi.stockage``.

Le dossier a été **renommé** ``suivi/stockage/`` : ce sont des **backends de
stockage** (implémentations du port ``StockageAbstraite``), pas des adaptateurs
au sens du patron :class:`automatheque.conception.structures.Adaptateur` (qui,
lui, injecte dynamiquement des méthodes). Le nom prêtait à confusion dans un
dépôt qui nomme explicitement ses patrons.

Importer depuis ce chemin émet un ``DeprecationWarning``. Préférer
``from automatheque.suivi.stockage.repertoire import StockageRepertoire`` — ou,
API publique, ``from automatheque.suivi.journal import StockageRepertoire``.
"""

import warnings

from automatheque.suivi.stockage.repertoire import StockageRepertoire  # noqa: F401

__all__ = ["StockageRepertoire"]

warnings.warn(
    "automatheque.suivi.adaptateurs est déprécié : le dossier a été renommé "
    "automatheque.suivi.stockage. Importez depuis "
    "automatheque.suivi.stockage.repertoire (ou automatheque.suivi.journal). "
    "Ce shim sera supprimé dans une version ultérieure.",
    DeprecationWarning,
    stacklevel=2,
)
