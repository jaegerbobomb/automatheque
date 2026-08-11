# -*- coding: utf-8 -*-
from datetime import datetime
from email.header import Header
from email.utils import format_datetime, formataddr, formatdate, parseaddr
from pathlib import Path
from typing import Callable, List, Sequence, Tuple, Union

import attr

# `maintenant` vient désormais de la primitive partagée `schema.temps` (#48).
# Ré-exportée ici pour rester importable depuis `courriel` (rétro-compat) et
# servir de fabrique à `_date_envoi`.
from automatheque.schema.temps import maintenant as maintenant


@attr.s
class Courriel:
    """Classe destinée à manipuler des courriels.

    Cette classe est un wrapper de "email".

    La validité des emails est testée de manière très sommaire par défaut.
    Si besoin, utiliser pyIsEmail ou autre librairie, à passer à
    "self.teste_adresse_valide".
    Pour l'instant on se contente de ça : https://stackoverflow.com/a/14485817/8721626
    """

    sujet: str = attr.ib(kw_only=True)
    _emetteur: Union[tuple, str] = attr.ib(default=None, kw_only=True)
    _destinataires: Sequence[Union[tuple, str]] = attr.ib(factory=list, kw_only=True)
    contenu: str = attr.ib(init=False, default="", kw_only=True)
    pieces_jointes: List[Path] = attr.ib(init=False, factory=list, kw_only=True)
    # ATTENTION : ``factory`` (et non ``default=datetime.now()``) est
    # indispensable. Un ``default`` est évalué **une seule fois**, à la
    # définition de la classe : toutes les instances partageraient alors
    # l'horodatage figé de l'import. La fabrique est rappelée à chaque
    # instanciation. Cf. #25.
    _date_envoi: datetime = attr.ib(init=False, factory=maintenant, kw_only=True)
    teste_adresse_valide: Callable[[str], Tuple[bool, str]] = attr.ib(
        init=False, default=lambda e: ("@" in e, ""), kw_only=True
    )

    def __attrs_post_init__(self):
        """Fait passer les valeurs du constructeur par la même validation que
        les setters.

        attrs affecte `_emetteur`/`_destinataires` **en direct**, sans passer
        par `@emetteur.setter`/`@destinataires.setter` (validation +
        normalisation `formataddr`). Sans ce post-init,
        `Courriel(emetteur="pas-un-email")` passerait là où
        `c.emetteur = "pas-un-email"` lève, et un tuple `("Bob", "bob@x")`
        resterait brut au lieu d'être formaté. Un émetteur non fourni (`None`)
        reste permis : il est souvent rempli plus tard (p. ex. par `factrice`).
        """
        if self._emetteur is not None:
            self._emetteur = self._controle_format_email(self._emetteur, "emetteur")
        if self._destinataires:
            # Rejoue le setter (valide, normalise, gère la chaîne unique).
            self.destinataires = self._destinataires

    def _controle_format_email(self, valeur: Union[tuple, str], champ: str):
        """Renvoie l'email contrôlé pour le champ indiqué.

        Conformément à https://docs.python.org/3/library/email.utils.html
        les emails doivent avoir un format particulier : soit une chaine que
        l'on peut décomposer avec parseaddr, soit un tuple que l'on peut
        formater avec formataddr.

        :param valeur: tuple ou string contenant nom et email
        :param champ: champ à contrôler
        """
        err = f"{champ} doit etre une chaine ou un tuple conforme à parseaddr/formataddr cf: https://docs.python.org/3/library/email.utils.html"  # noqa
        if isinstance(valeur, str):
            (nom, adresse) = parseaddr(valeur)
            if (nom, adresse) == ("", ""):
                raise ValueError(err)
        elif isinstance(valeur, tuple) and len(valeur) == 2:
            (nom, adresse) = valeur
        else:
            raise ValueError(err)
        valide, raison = self.teste_adresse_valide(adresse)
        if not valide:
            raise ValueError(raison if raison else "Adresse courriel invalide")
        return formataddr((str(Header(nom)), adresse))

    @property
    def emetteur(self):
        """Renvoie l'émetteur."""
        return self._emetteur

    @emetteur.setter
    def emetteur(self, valeur):
        """Vérifie que emetteur a un format correct avant affectation."""
        self._emetteur = self._controle_format_email(valeur, "emetteur")

    @property
    def destinataires(self):
        """Renvoie les destinataires."""
        return self._destinataires

    @destinataires.setter
    def destinataires(self, valeur):
        """Ajoute les destinataires à la liste."""
        # Une chaîne unique est **un** destinataire, pas une suite de
        # caractères : `for d in "solo@x.com"` itérerait `s`, `o`, `l`… et
        # `_controle_format_email` lèverait sur le premier. Toute autre séquence
        # (liste, tuple de destinataires) est parcourue telle quelle.
        if isinstance(valeur, str):
            valeur = [valeur]
        self._destinataires = []  # Ràz destinataires
        for d in valeur or []:
            self.ajouter_destinataire(d)

    def ajouter_piece_jointe(self, fichier: Path):
        """Ajoute une pièce jointe au message."""
        self.pieces_jointes.append(fichier)

    def ajouter_destinataire(self, destinataire):
        """Ajoute un destinataire au message."""
        destinataire = self._controle_format_email(destinataire, "destinataire")
        self._destinataires.append(destinataire)

    @property
    def mimetext(self):
        return "html" if self.contenu.startswith("<html") else "plain"

    @property
    def date_envoi(self):
        """Date d'envoi au format RFC 5322 (en-tête ``Date`` d'un courriel)."""
        if self._date_envoi and isinstance(self._date_envoi, datetime):
            if self._date_envoi.tzinfo is not None:
                # datetime tz-aware : l'offset est écrit explicitement.
                return format_datetime(self._date_envoi)
            # Rétro-compat : un datetime naïf est supposé être en heure locale.
            return formatdate(datetime.timestamp(self._date_envoi), localtime=True)
