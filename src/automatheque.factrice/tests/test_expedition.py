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


def _config_oauth():
    """Config SMTP en mode OAuth (BYO oauth_cmd)."""
    c = _config_smtp()
    c.set("factrice.smtp", "oauth", "1")
    c.set("factrice.smtp", "oauth_client_id", "cid")
    return c


def test_oauth_cmd_absent_leve_dependance_manquante(monkeypatch):
    """#27 : un `oauth_cmd` introuvable → `DependanceManquante` claire."""
    from automatheque.exceptions import DependanceManquante

    fake = MagicMock()
    monkeypatch.setattr(expedition.smtplib, "SMTP_SSL", lambda *a, **k: fake)
    c = _config_oauth()
    c.set("factrice.smtp", "oauth_cmd", "outil-oauth-inexistant-xyz")

    with pytest.raises(DependanceManquante):
        ExpeditriceSmtp(config=c)


def test_oauth_cmd_present_utilise_le_jeton(monkeypatch):
    """#27 : le jeton produit par `oauth_cmd` est envoyé via AUTH XOAUTH2."""
    fake = MagicMock()
    monkeypatch.setattr(expedition.smtplib, "SMTP_SSL", lambda *a, **k: fake)
    faux_exec = MagicMock()
    faux_exec.exec.return_value = MagicMock(stdout="LE-JETON\n")
    monkeypatch.setattr(expedition, "charge_dependance", lambda *a, **k: faux_exec)

    c = _config_oauth()
    c.set("factrice.smtp", "oauth_cmd", "oama access user")
    ExpeditriceSmtp(config=c)

    # cmd/args découpés, jeton nettoyé, envoyé en XOAUTH2.
    assert faux_exec.exec.call_args.args == ("access", "user")
    fake.ehlo.assert_called_once_with("cid")
    methode, charge = fake.docmd.call_args.args
    assert methode == "AUTH"
    assert charge == "XOAUTH2 LE-JETON"


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


# --- #24 : validator attrs sur `config` -------------------------------------


def test_config_non_configparser_leve(monkeypatch):
    """#24 : un `config` qui n'est pas un ConfigParser est rejeté à la construction."""
    with pytest.raises(TypeError):
        ExpeditriceSmtp(config="pas-un-configparser")


def test_config_none_reste_accepte(monkeypatch):
    """`config=None` reste valide (le validator est `optional`)."""
    fake = MagicMock()
    monkeypatch.setattr(expedition.smtplib, "SMTP_SSL", lambda *a, **k: fake)
    # config non fourni → charge_configuration() ; on le neutralise.
    monkeypatch.setattr(
        expedition, "charge_configuration", lambda *a, **k: _config_smtp()
    )
    ExpeditriceSmtp()  # ne doit pas lever au titre du validator


# --- #27 : émetteur par défaut configurable + nom de fichier temporaire sûr --


def _esmtp_avec_config(monkeypatch, config):
    """ExpeditriceEsmtp dont l'exécutant réussit, avec la ``config`` donnée."""
    process = MagicMock(returncode=0, stderr=b"")
    process.check_returncode.return_value = None
    executant = MagicMock()
    executant.exec.return_value = process
    monkeypatch.setattr(expedition, "charge_dependance", lambda *a, **k: executant)
    return ExpeditriceEsmtp(config=config)


def test_esmtp_emetteur_par_defaut_configurable(monkeypatch):
    """L'émetteur par défaut vient de `[factrice.esmtp] emetteur`."""
    conf = ConfigParser()
    conf.add_section("factrice.esmtp")
    conf.set("factrice.esmtp", "emetteur", "boite@ex.fr")
    exp = _esmtp_avec_config(monkeypatch, conf)

    courriel = Courriel(sujet="sujet", destinataires=["dest@ex.fr"])  # emetteur None
    exp.expedie(courriel)
    assert courriel.emetteur == "boite@ex.fr"


def test_esmtp_emetteur_par_defaut_repli_historique(monkeypatch):
    """Sans configuration, l'émetteur retombe sur `osuser@localhost`."""
    exp = _esmtp_avec_config(monkeypatch, ConfigParser())

    courriel = Courriel(sujet="sujet", destinataires=["dest@ex.fr"])
    exp.expedie(courriel)
    assert courriel.emetteur == "osuser@localhost"


def test_esmtp_sujet_avec_separateur_ne_casse_pas_le_chemin(monkeypatch):
    """Un sujet contenant un `/` ne crée plus de sous-répertoire inexistant.

    L'ancien nommage `/tmp/<date>_<sujet>.txt` plantait (`FileNotFoundError`)
    pour un sujet du type `rapport/2026`. Le fichier temporaire assaini règle
    le problème.
    """
    exp = _esmtp_avec_config(monkeypatch, ConfigParser())

    courriel = Courriel(
        emetteur="exp@ex.fr", sujet="rapport/2026", destinataires=["dest@ex.fr"]
    )
    assert exp.expedie(courriel) == 0
