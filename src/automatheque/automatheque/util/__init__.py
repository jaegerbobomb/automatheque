"""Package comprenant quelques outils classiques."""

# Imports depuis fichier
from .fichier import enleve_caracteres_invalides

# Imports depuis parallele
from .parallele import Resultat, parallelise

# Imports depuis reessaye
from .reessaye import reessaye

# Imports depuis repertoire
from .repertoire import mkdir_p

# Imports depuis structures_python
from .structures_python import dict_merge

# Imports depuis temps
from .temps import (
    FR,
    Vocabulaire,
    humanise_duree,
    humanise_relatif,
    parse_date_floue,
    parse_duree,
)

__all__ = [
    # .fichier
    "enleve_caracteres_invalides",
    # .parallele
    "parallelise",
    "Resultat",
    # .reessaye
    "reessaye",
    # .repertoire
    "mkdir_p",
    # .structures_python
    "dict_merge",
    # .temps
    "parse_duree",
    "humanise_duree",
    "humanise_relatif",
    "Vocabulaire",
    "FR",
    "parse_date_floue",
]
