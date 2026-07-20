# -*- coding: utf-8 -*-
"""Tests de construction du message MIME par PreparatriceSmtp.

Aucun réseau : on vérifie uniquement l'objet ``email.mime`` retourné.
"""

from email.message import Message

import pytest
from automatheque.factrice.preparation import (
    SEPARATEUR_DESTINATAIRES,
    Preparatrice,
    PreparatriceSmtp,
)
from automatheque.schema.texte import Courriel


def _courriel(**kwargs):
    """Construit un Courriel prêt pour la préparation."""
    c = Courriel(
        sujet=kwargs.get("sujet", "Sujet du mail"),
        emetteur=kwargs.get("emetteur", "src@mail.com"),
    )
    c.ajouter_destinataire("user@tld.com")
    return c


def test_preparatrice_base_non_implementee():
    """La classe de base ne sait rien préparer."""
    with pytest.raises(NotImplementedError):
        Preparatrice.prepare(_courriel())


def test_prepare_construit_entetes():
    """Sujet / From / To / Date sont positionnés depuis le Courriel."""
    c = _courriel()
    c.ajouter_destinataire("Toto <toto@tld.com>")

    msg = PreparatriceSmtp.prepare(c)

    assert isinstance(msg, Message)
    assert msg["Subject"] == "Sujet du mail"
    assert msg["From"] == "src@mail.com"
    assert msg["To"] == SEPARATEUR_DESTINATAIRES.join(c.destinataires)
    assert msg["Date"] == c.date_envoi
    assert msg.preamble == "Sujet du mail"
    assert msg.is_multipart()


def test_prepare_corps_texte_plain():
    """Un contenu simple produit une partie text/plain."""
    c = _courriel()
    c.contenu = "Bonjour"

    msg = PreparatriceSmtp.prepare(c)

    parties = msg.get_payload()
    assert parties[0].get_content_type() == "text/plain"
    assert parties[0].get_payload() == "Bonjour"


def test_prepare_corps_html():
    """Un contenu commençant par <html produit une partie text/html."""
    c = _courriel()
    c.contenu = "<html><body>Salut</body></html>"

    msg = PreparatriceSmtp.prepare(c)

    partie = msg.get_payload()[0]
    assert partie.get_content_type() == "text/html"


def test_prepare_avec_piece_jointe(tmp_path):
    """La pièce jointe est lue et attachée au message."""
    fichier = tmp_path / "document.txt"
    fichier.write_bytes(b"contenu binaire")

    c = _courriel()
    c.contenu = "Voir pièce jointe"
    c.ajouter_piece_jointe(fichier)

    msg = PreparatriceSmtp.prepare(c)

    parties = msg.get_payload()
    assert len(parties) == 2  # corps + 1 pièce jointe
    pj = parties[1]
    assert pj.get_content_type() == "application/octet-stream"
    # NB : `preparation.py` passe Content_Disposition / Name en **paramètres du
    # Content-Type** (kwargs de MIMEApplication), pas dans un header dédié.
    assert pj.get_param("name") == "document.txt"
    assert 'filename="document.txt"' in pj.get_param("content-disposition")
    assert pj.get_payload(decode=True) == b"contenu binaire"
