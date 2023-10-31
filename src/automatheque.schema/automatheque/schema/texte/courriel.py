# -*- coding: utf-8 -*-
from datetime import datetime
from email.header import Header
from email.utils import formataddr, formatdate, parseaddr
from typing import Callable, List, Sequence, Tuple, Union

import attr

# from automatheque.schema.medium import Medium


@attr.s
class Courriel:
    """Classe destinée à manipuler des courriels.

    Cette classe est un wrapper de "email".

    La validité des emails est testée de manière très sommaire par défaut.
    Si besoin, utiliser pyIsEmail ou autre librairie, à passer à "self.teste_adresse_valide".
    Pour l'instant on se contente de ça : https://stackoverflow.com/a/14485817/8721626
    """

    sujet: str = attr.ib(kw_only=True)
    _emetteur: Union[tuple, str] = attr.ib(kw_only=True)
    _destinataires: Sequence[Union[tuple, str]] = attr.ib(factory=list, kw_only=True)
    contenu: str = attr.ib(init=False, default="", kw_only=True)
    pieces_jointes: List[str] = attr.ib(init=False, factory=list, kw_only=True)
    _date_envoi: datetime = attr.ib(
        init=False, default=None, kw_only=True
    )  # TODO vérifier les timezones
    teste_adresse_valide: Callable[[str], Tuple[bool, str]] = attr.ib(
        init=False, default=lambda e: ("@" in e, ""), kw_only=True
    )

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
        self._destinataires = []  # Ràz destinataires
        for d in [d for d in valeur or []]:
            self.ajouter_destinataire(d)

    def ajouter_piece_jointe(self, fichier):
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
        if self._date_envoi and isinstance(self._date_envoi, datetime):
            return formatdate(datetime.timestamp(self._date_envoi))
