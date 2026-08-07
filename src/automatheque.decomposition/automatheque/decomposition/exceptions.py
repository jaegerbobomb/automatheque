# -*- coding: utf-8 -*-
"""Exceptions propres à la décomposition.

Elles héritent de :class:`automatheque.exceptions.AutomathequeBaseException`
afin que le code appelant puisse filtrer d'un seul `except` toutes les
exceptions de l'automathèque.
"""

from automatheque.exceptions import AutomathequeBaseException


class DecompositionEchecTousPatrons(AutomathequeBaseException):
    """Aucun patron n'a permis de décomposer la source."""

    def __init__(self, msg="Aucun patron trouvé."):
        """Initialisation."""
        self.msg = msg
        super().__init__(self.msg)


class DecompositionEchecPatron(AutomathequeBaseException):
    """La décomposition a échoué pour le patron donné.

    Levée pour *un* patron : c'est une étape normale de l'algorithme, qui
    essaie les patrons les uns après les autres. Seule
    :class:`DecompositionEchecTousPatrons` signale un échec définitif.
    """

    def __init__(self, patron):
        """Initialisation."""
        self.patron = patron
        self.msg = "Décomposition échouée pour le patron '{}'.".format(patron)
        super().__init__(self.msg)
