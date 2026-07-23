import datetime
import functools
import inspect

import attr

from automatheque.suivi.adaptateurs.repertoire import StockageRepertoire
from automatheque.suivi.ports import StockageAbstraite
from automatheque.util.fichier import enleve_caracteres_invalides

#: Fabriques de « sceau » de date par période : la clé de suivi inclut ce sceau,
#: de sorte qu'une nouvelle période produit une nouvelle clé (donc un rejeu).
_SCEAUX_DATE = {
    "jour": lambda d: d.isoformat(),
    "semaine": lambda d: "{}-S{:02d}".format(*d.isocalendar()[:2]),
    "mois": lambda d: d.strftime("%Y-%m"),
    "annee": lambda d: str(d.year),
}


@attr.s
class JournalSuivi:
    """Journal de suivi d'une action quelconque.

    Exemple:

    >>> from pathlib import Path
    >>> from automatheque.suivi.journal import JournalSuivi, StockageRepertoire

    >>> stockage = StockageRepertoire(Path("/chemin/vers/stockage/suivi"))
    >>> journal = JournalSuivi(stockage)

    >>> if not journal.deja_fait(identifiant_unique_action):
    >>>     action_quelconque()
    >>>     journal.coche(identifiant_unique_action, contenu)
    """

    stockage: StockageAbstraite = attr.ib(default=StockageRepertoire())  # handler ?

    def deja_fait(self, reference: str) -> bool:
        return self.stockage.existe(reference)

    def _cle_suivi(self, nom_fonction, reference, periode=None, date=None):
        """Construit la clé de suivi ``nom_fonction_reference`` (+ sceau de date).

        Assainie (`enleve_caracteres_invalides`) car elle sert de nom de
        fichier au stockage. Cf. #27.
        """
        cle = "{}_{}".format(nom_fonction, reference)
        if periode is not None:
            if periode not in _SCEAUX_DATE:
                raise ValueError(
                    "période inconnue : {!r} (attendu : {}).".format(
                        periode, ", ".join(_SCEAUX_DATE)
                    )
                )
            jour = date or datetime.date.today()
            cle = "{}_{}".format(cle, _SCEAUX_DATE[periode](jour))
        return enleve_caracteres_invalides(cle)

    def ni_fait_ni_à_refaire(self, nom_arg_reference, periode=None, date=None):
        """Décore une fonction pour qu'elle ne soit jouée qu'une fois par référence.

        La référence est lue dans l'argument ``nom_arg_reference`` de la fonction
        décorée ; la clé de suivi sauvegardée est ``nom_fonction_reference``. Si
        l'action a déjà été jouée pour cette clé, la fonction n'est **pas**
        rappelée et le décorateur renvoie ``None``.

        :param nom_arg_reference: nom du paramètre de la fonction décorée qui
            porte la référence unique de l'action.
        :param periode: si fournie, l'action redevient **rejouable à chaque
            nouvelle période** (le sceau de date entre dans la clé). Valeurs :
            ``"jour"``, ``"semaine"``, ``"mois"``, ``"annee"``. Défaut ``None`` =
            une seule fois, définitivement. Cf. #27.
        :param date: date de référence pour le sceau (défaut : le jour de l'appel).
            Surtout utile pour tester de façon déterministe.

        .. code-block:: python

            @journal.ni_fait_ni_à_refaire("identifiant")
            def traite(identifiant):
                ...  # joué une seule fois par identifiant

            @journal.ni_fait_ni_à_refaire("flux", periode="jour")
            def synchronise(flux):
                ...  # rejoué au plus une fois par jour et par flux
        """

        def decorateur(fonction):
            @functools.wraps(fonction)
            def enveloppe(*args, **kwargs):
                lies = inspect.signature(fonction).bind(*args, **kwargs)
                lies.apply_defaults()
                if nom_arg_reference not in lies.arguments:
                    raise KeyError(
                        "paramètre {!r} absent de l'appel à {}().".format(
                            nom_arg_reference, fonction.__name__
                        )
                    )
                reference = lies.arguments[nom_arg_reference]
                cle = self._cle_suivi(fonction.__name__, reference, periode, date)
                if self.deja_fait(cle):
                    return None
                resultat = fonction(*args, **kwargs)
                self.coche(cle, "" if resultat is None else str(resultat))
                return resultat

            return enveloppe

        return decorateur

    def coche(self, reference: str, contenu: str) -> bool:
        return self.stockage.sauvegarde(reference, contenu)
