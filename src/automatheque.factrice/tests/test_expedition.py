import smtplib
from configparser import ConfigParser
from unittest.mock import MagicMock

import pytest
from automatheque.factrice import expedition
from automatheque.factrice.expedition import ExpeditriceSmtp


def _config_smtp():
    """Configuration SMTP minimale (ssl pour éviter la branche starttls)."""
    c = ConfigParser()
    c.add_section("factrice.smtp")
    c.set("factrice.smtp", "ssl", "1")
    c.set("factrice.smtp", "hote", "localhost")
    c.set("factrice.smtp", "identifiant", "user")
    c.set("factrice.smtp", "mdp", "secret")
    return c


def test_smtp_exception_pendant_connexion_est_capturee(monkeypatch):
    """Une erreur SMTP à la connexion est journalisée, pas propagée."""
    fake = MagicMock()
    fake.login.side_effect = smtplib.SMTPAuthenticationError(535, b"bad creds")
    monkeypatch.setattr(expedition.smtplib, "SMTP_SSL", lambda *a, **k: fake)

    # Ne doit pas lever :
    ExpeditriceSmtp(config=_config_smtp())
    fake.login.assert_called_once()


def test_erreur_non_smtp_pendant_connexion_se_propage(monkeypatch):
    """Une erreur non-SMTP n'est plus avalée silencieusement : elle remonte.

    Régression : auparavant ``except Exception: pass`` masquait toutes les
    erreurs, y compris celles sans rapport avec le protocole SMTP.
    """
    fake = MagicMock()
    fake.login.side_effect = ValueError("erreur inattendue")
    monkeypatch.setattr(expedition.smtplib, "SMTP_SSL", lambda *a, **k: fake)

    with pytest.raises(ValueError):
        ExpeditriceSmtp(config=_config_smtp())
