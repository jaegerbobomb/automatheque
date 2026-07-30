# -*- coding: utf-8 -*-

from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from automatheque.conception.structures import Monteur
from automatheque.schema.texte import Courriel

SEPARATEUR_DESTINATAIRES = ", "


class Preparatrice(Monteur):
    """**Monteur** de la représentation transportable d'un :class:`Courriel`.

    Patron **Monteur** (cf. :class:`automatheque.conception.structures.Monteur`) :
    la construction du message (sujet, expéditeur, date, corps, pièces jointes —
    beaucoup de champs optionnels, cas d'usage type du Monteur) est séparée de sa
    représentation. Une sous-classe concrète implémente :meth:`construit` pour un
    format donné (ici MIME multipart pour SMTP).
    """

    def construit(self, courriel: Courriel):
        """Construit la représentation transportable du courriel."""
        raise NotImplementedError


class PreparatriceSmtp(Preparatrice):
    def construit(self, courriel: Courriel):
        """Construit l'objet Multipart (MIME) à envoyer et le retourne."""
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
                        Content_Disposition=(
                            f'attachment; filename="{piece_jointe.name}"'
                        ),
                        Name=piece_jointe.name,
                    )
                )
        return _msg
