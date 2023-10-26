# -*- coding: utf-8 -*-
from datetime import datetime
from os.path import basename
import os

import attr
from email.header import Header
from email.utils import formatdate, formataddr, parseaddr

#from automatheque.schema.medium import Medium


@attr.s
class Courriel():
    """Classe destinée à manipuler des courriels.

    Cette classe est un wrapper de "email".
    """
    EXTENSIONS = ['eml']

    def __init__(self, appelant=None, sujet=None, contenu='',
                 destinataires=None, emetteur=None, pieces_jointes=None):
        """__init__.

        :param appelant:       le nom de l'appelant
        :param sujet:          le sujet du mail (sera concaténé avec appelant)
        :param contenu:        contenu du courriel
        :param destinataires:  liste des adresses de courriel des destinataires
        :param emetteur:       adresse de courriel de l'emetteur
        :param pieces_jointes: liste des pièces jointes
        """
        self.appelant = appelant
        self.sujet = sujet if not appelant else '[{}] {}'.format(
            appelant, sujet)
        self.contenu = contenu
        self.destinataires = destinataires
        self._emetteur = emetteur
        self.pieces_jointes = [] if not pieces_jointes else pieces_jointes
        self.mimetext = 'html' if self.contenu.startswith('<html') else 'plain'
        self._date_envoi = None  # Doit etre une datetime si pas vide # TODO vérifier les timezones
        self._msg = None  # Message complet
        
    def _controle_format_email(self, valeur, champ):
        """Renvoie l'email contrôlé pour le champ indiqué.
        
        Conformément à https://docs.python.org/3/library/email.utils.html 
        les emails doivent avoir un format particulier : soit une chaine que
        l'on peut décomposer avec parseaddr, soit un tuple que l'on peut
        formater avec formataddr.
        
        :param valeur: tuple ou string contenant nom et email
        :param champ: champ à contrôler
        """
        err = "{} doit etre une chaine ou un tuple conforme à parseaddr/formataddr cf: https://docs.python.org/3/library/email.utils.html".format(champ)
        if isinstance(valeur, str):
            (nom, email) = parseaddr(valeur)
            if (nom, email) == ('', ''):
                raise ValueError(err)
        elif isinstance(valeur, tuple) and len(valeur) == 2:
            (nom, email) = valeur
        else:
            raise ValueError(err)
        # TODO il faudrait aussi vérifier que email est conforme !!
        return formataddr((str(Header(nom)), email))
        
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
        self.destinataires.append(destinataire)

    @property
    def date_envoi(self):
        if self._date_envoi and isinstance(self._date_envoi, datetime):
            return formatdate(datetime.timestamp(self._date_envoi))

    def charge_utile(self):
        """Renvoie la charge utile du courriel, à utiliser avec esmtp.

        TODO supprimer et mettre dans un StockageCourrielEsmtp par ex.
        """
        res = u'Subject: {}\nMime-Version: 1.0;\nContent-Type: text/html; charset="ISO-8859-1";\nContent-Transfer-Encoding: 7bit;\n\n{}\n'.format(
            self.sujet, self.contenu).encode('utf-8')
        return res

