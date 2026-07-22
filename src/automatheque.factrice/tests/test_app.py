"""Tests de l'application ``factrice`` (app/__init__.py, #27).

Le module redevient importable sans effet de bord (le câblage
``@script_automatheque`` est différé dans ``main``), ce qui rend ces tests
possibles.
"""

import io

from automatheque.factrice import app
from automatheque.factrice.app import envoi_mail_simple, recupere_texte


def test_recupere_texte_argument_prioritaire():
    """Le texte fourni en argument est utilisé tel quel."""
    assert recupere_texte({"<texte_du_mail>": "coucou"}) == "coucou"


def test_recupere_texte_depuis_stdin(monkeypatch):
    """#27 : sans argument, le corps est lu sur l'entrée standard (`cat | factrice`)."""
    monkeypatch.setattr("sys.stdin", io.StringIO("depuis le tuyau"))
    assert recupere_texte({"<texte_du_mail>": None}) == "depuis le tuyau"


def test_envoi_mail_simple_smtp_construit_le_courriel(monkeypatch):
    """Sans `--via-esmtp` : route vers SMTP et construit un Courriel cohérent."""
    envoye = {}

    class FakeSmtp:
        def __init__(self, *a, **k):
            pass

        def expedie(self, mail):
            envoye["mail"] = mail

    monkeypatch.setattr(app, "ExpeditriceSmtp", FakeSmtp)
    app.envoi_mail_simple("sujet", "a@b.c,d@e.f", "corps", via_esmtp=False)

    mail = envoye["mail"]
    assert mail.sujet == "sujet"
    assert mail.destinataires == ["a@b.c", "d@e.f"]
    assert mail.contenu == "corps"


def test_envoi_mail_simple_esmtp_renvoie_le_code(monkeypatch):
    """Avec `--via-esmtp` : route vers esmtp et renvoie son code de retour."""

    class FakeEsmtp:
        def __init__(self, *a, **k):
            pass

        def expedie(self, mail):
            return 7

    monkeypatch.setattr(app, "ExpeditriceEsmtp", FakeEsmtp)
    assert envoi_mail_simple("s", "a@b.c", "corps", via_esmtp=True) == 7
