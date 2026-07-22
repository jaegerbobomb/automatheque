import logging
import smtplib
import subprocess
from configparser import ConfigParser
from unittest.mock import MagicMock

import pytest
from automatheque.factrice import expedition
from automatheque.factrice.expedition import ExpeditriceEsmtp, ExpeditriceSmtp
from automatheque.schema.texte import Courriel


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


# --- ExpeditriceEsmtp : gestion du code de retour (#26) ---------------------


def _esmtp(monkeypatch, process):
    """Construit une ExpeditriceEsmtp dont l'exécutant renvoie ``process``."""
    executant = MagicMock()
    executant.exec.return_value = process
    monkeypatch.setattr(expedition, "charge_dependance", lambda *a, **k: executant)
    return ExpeditriceEsmtp(config=ConfigParser())


def _courriel():
    return Courriel(emetteur="exp@ex.fr", sujet="sujet", destinataires=["dest@ex.fr"])


def test_esmtp_succes_renvoie_le_code_retour(monkeypatch, tmp_path):
    process = MagicMock(returncode=0, stderr=b"")
    process.check_returncode.return_value = None
    exp = _esmtp(monkeypatch, process)
    assert exp.expedie(_courriel()) == 0


def test_esmtp_echec_journalise_et_renvoie_le_code(monkeypatch, caplog):
    """`check_returncode` peut lever : l'erreur est journalisée, pas propagée."""
    process = MagicMock(returncode=42, stderr=b"boum esmtp")
    process.check_returncode.side_effect = subprocess.CalledProcessError(
        42, "esmtp", stderr=b"boum esmtp"
    )
    exp = _esmtp(monkeypatch, process)
    with caplog.at_level(logging.ERROR, logger="automatheque.factrice.expedition"):
        code = exp.expedie(_courriel())
    assert code == 42
    assert any("esmtp" in r.getMessage() for r in caplog.records)
