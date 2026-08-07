# -*- coding: utf-8 -*-
"""Décomposition de chaînes et d'arborescences par patrons."""

from .decomposeur import (
    DECOMPOSE_ANALYSE_ARBO_COMPLETE,
    DECOMPOSE_ANALYSE_ARBO_CONCATENE,
    DECOMPOSE_ANALYSE_ARBO_UN_NIVEAU,
    DECOMPOSE_RESULTAT_CUMULE,
    DECOMPOSE_RESULTAT_MAX_INFOS,
    DECOMPOSE_RESULTAT_PREMIER_NON_NUL,
    Decomposable,
    Decomposeur,
    Decomposeurs,
    Identificateur,
)
from .exceptions import DecompositionEchecPatron, DecompositionEchecTousPatrons

__all__ = [
    "DECOMPOSE_ANALYSE_ARBO_COMPLETE",
    "DECOMPOSE_ANALYSE_ARBO_CONCATENE",
    "DECOMPOSE_ANALYSE_ARBO_UN_NIVEAU",
    "DECOMPOSE_RESULTAT_CUMULE",
    "DECOMPOSE_RESULTAT_MAX_INFOS",
    "DECOMPOSE_RESULTAT_PREMIER_NON_NUL",
    "Decomposable",
    "Decomposeur",
    "Decomposeurs",
    "DecompositionEchecPatron",
    "DecompositionEchecTousPatrons",
    "Identificateur",
]
