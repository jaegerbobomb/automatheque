# -*- coding: utf-8 -*-
"""Tests du module secret (objet caviardé + greffons résolveurs, #8)."""

from configparser import ConfigParser
from typing import Optional
from unittest.mock import MagicMock

from automatheque.secret import (
    GreffonSecretCommande,
    GreffonSecretConfig,
    GreffonSecretEnv,
    GreffonSecretKeyring,
    ResoudreSecret,
    Secret,
    recup_secret,
)

# --- Secret : caviardage -----------------------------------------------------


def test_secret_reveler_renvoie_la_valeur():
    assert Secret("mon-mot-de-passe").reveler() == "mon-mot-de-passe"


def test_secret_str_est_caviarde():
    s = Secret("mon-mot-de-passe")
    assert str(s) == "***"
    assert "mon-mot-de-passe" not in str(s)


def test_secret_repr_est_caviarde():
    s = Secret("mon-mot-de-passe")
    assert repr(s) == "Secret(***)"
    assert "mon-mot-de-passe" not in repr(s)


def test_secret_ne_fuite_pas_en_fstring_ni_format():
    s = Secret("xyz")
    assert f"mdp={s}" == "mdp=***"
    assert "mdp={}".format(s) == "mdp=***"
    assert "mdp=%s" % s == "mdp=***"


def test_secret_ne_fuite_pas_dans_les_logs(caplog):
    import logging

    s = Secret("ultra-secret")
    with caplog.at_level(logging.INFO):
        logging.getLogger("t").info("mdp=%s", s)
    assert "ultra-secret" not in caplog.text
    assert "***" in caplog.text


# --- Greffons résolveurs -----------------------------------------------------


def test_greffon_env(monkeypatch):
    monkeypatch.setenv("FACTRICE_SMTP_MDP", "depuis-env")
    g = GreffonSecretEnv()
    assert g.resout_secret("factrice.smtp.mdp") == "depuis-env"
    assert g.resout_secret("absente.quelque.part") is None


def test_greffon_config():
    c = ConfigParser()
    c.add_section("factrice.smtp")
    c.set("factrice.smtp", "mdp", "depuis-config")
    g = GreffonSecretConfig(source=c)
    assert g.resout_secret("factrice.smtp.mdp") == "depuis-config"
    assert g.resout_secret("factrice.smtp.absente") is None  # option absente
    assert g.resout_secret("section.inexistante.x") is None  # section absente
    assert g.resout_secret("sanspoint") is None  # pas de section extractible


def test_greffons_declarent_bien_la_capacite():
    """Chaque greffon résolveur déclare la capacité ResoudreSecret."""
    for classe in (
        GreffonSecretEnv,
        GreffonSecretConfig,
        GreffonSecretKeyring,
        GreffonSecretCommande,
    ):
        assert ResoudreSecret in classe.CAPACITES


def test_greffon_keyring_absent_est_neutre(monkeypatch):
    """Sans le paquet `keyring`, le greffon renvoie None (ne casse pas)."""
    import builtins

    vrai_import = builtins.__import__

    def faux_import(nom, *a, **k):
        if nom == "keyring":
            raise ImportError("pas de keyring")
        return vrai_import(nom, *a, **k)

    monkeypatch.setattr(builtins, "__import__", faux_import)
    assert GreffonSecretKeyring().resout_secret("factrice.smtp.mdp") is None


def test_greffon_commande(monkeypatch):
    """La sortie de la commande (nettoyée) devient le secret."""
    faux_exec = MagicMock()
    faux_exec.exec.return_value = MagicMock(stdout="  le-jeton\n")
    classe = MagicMock(return_value=faux_exec)
    monkeypatch.setattr("automatheque.util.dependances_externes.Executant", classe)

    g = GreffonSecretCommande(gabarit="pass show {cle}")
    assert g.resout_secret("factrice.smtp.mdp") == "  le-jeton"  # strip \n seulement
    # cmd/args découpés par shlex, {cle} substituée
    classe.assert_called_once_with("pass")
    assert faux_exec.exec.call_args.args == ("show", "factrice.smtp.mdp")


# --- recup_secret : résolution ordonnée --------------------------------------


def test_recup_secret_depuis_env(monkeypatch):
    monkeypatch.setenv("FACTRICE_SMTP_MDP", "e")
    s = recup_secret("factrice.smtp.mdp")
    assert isinstance(s, Secret)
    assert s.reveler() == "e"


def test_recup_secret_depuis_config(monkeypatch):
    monkeypatch.delenv("FACTRICE_SMTP_MDP", raising=False)
    c = ConfigParser()
    c.add_section("factrice.smtp")
    c.set("factrice.smtp", "mdp", "c")
    assert recup_secret("factrice.smtp.mdp", config=c).reveler() == "c"


def test_recup_secret_env_prioritaire_sur_config(monkeypatch):
    monkeypatch.setenv("FACTRICE_SMTP_MDP", "env-gagne")
    c = ConfigParser()
    c.add_section("factrice.smtp")
    c.set("factrice.smtp", "mdp", "config-perd")
    assert recup_secret("factrice.smtp.mdp", config=c).reveler() == "env-gagne"


def test_recup_secret_introuvable_renvoie_none(monkeypatch):
    monkeypatch.delenv("FACTRICE_SMTP_MDP", raising=False)
    assert recup_secret("factrice.smtp.mdp") is None


def test_recup_secret_resolveurs_personnalises():
    """On peut fournir sa propre liste ordonnée de greffons résolveurs."""

    class ResolveurMuet:
        def resout_secret(self, cle: str) -> Optional[str]:
            return None

    class ResolveurFixe:
        def resout_secret(self, cle: str) -> Optional[str]:
            return "depuis-b2"

    s = recup_secret("x", resolveurs=[ResolveurMuet(), ResolveurFixe()])
    assert s.reveler() == "depuis-b2"
