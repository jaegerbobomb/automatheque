# -*- coding: utf-8 -*-
from pathlib import Path

from automatheque.schema.texte import Courriel
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication


SEPARATEUR_DESTINATAIRES = ", "


class Preparatrice:
    @classmethod
    def prepare(cls, courriel: Courriel):
        """Prépare le courriel pour le rendre expedit"able" ?"""
        raise NotImplementedError


class PreparatriceSmtp:
    @classmethod
    def prepare(cls, courriel: Courriel):
        """Construit l'objet Multipart à envoyer et le retourne."""
        _msg = MIMEMultipart()
        _msg["Subject"] = courriel.sujet
        _msg["From"] = courriel.emetteur
        _msg["To"] = SEPARATEUR_DESTINATAIRES.join(courriel.destinataires)
        _msg["Date"] = courriel.date_envoi
        _msg.preamble = courriel.sujet

        _msg.attach(MIMEText(courriel.contenu, _subtype=courriel.mimetext))

        for piece_jointe in courriel.pieces_jointes:
            with open(piece_jointe, "rb") as fic:
                _msg.attach(
                    MIMEApplication(
                        fic.read(),
                        Content_Disposition=f'attachment; filename="{piece_jointe.name}"',
                        Name=piece_jointe.name,
                    )
                )
        return _msg
