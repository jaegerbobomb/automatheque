"""Tests de ``Executant.exec`` (options subprocess explicites, #66)."""

import subprocess
import sys
from unittest.mock import MagicMock, patch

import pytest
from automatheque.util.dependances_externes import (
    Executant,
    _executable_fonctionne,
    recup_executable,
)


def _exec(*args, **kwargs):
    """Exécute avec ``subprocess.run`` mocké et renvoie le mock pour inspection."""
    with patch("automatheque.util.dependances_externes.subprocess.run") as run:
        run.return_value = MagicMock(returncode=0)
        Executant("/bin/truc").exec(*args, **kwargs)
    return run


def test_exec_construit_la_commande():
    """``args`` positionnels → tokens CLI, précédés de l'exécutable."""
    run = _exec("--action", "valeur")
    assert run.call_args.args[0] == ["/bin/truc", "--action", "valeur"]


def test_exec_capture_toujours_stdout_stderr():
    run = _exec()
    assert run.call_args.kwargs["stdout"] == subprocess.PIPE
    assert run.call_args.kwargs["stderr"] == subprocess.PIPE


def test_exec_propage_cwd_env_timeout():
    env = {"A": "1"}
    run = _exec(cwd="/tmp", env=env, timeout=5)
    kw = run.call_args.kwargs
    assert kw["cwd"] == "/tmp"
    assert kw["env"] == env
    assert kw["timeout"] == 5


def test_exec_stdin_herite_par_defaut():
    """#66 : par défaut, stdin est héritée (None), plus un PIPE jamais alimenté."""
    run = _exec()
    assert run.call_args.kwargs["stdin"] is None


def test_exec_stdin_explicite_transmis():
    sentinelle = object()
    run = _exec(stdin=sentinelle)
    assert run.call_args.kwargs["stdin"] is sentinelle


def test_exec_text_et_encoding():
    run = _exec(text=True, encoding="utf-8")
    kw = run.call_args.kwargs
    assert kw["text"] is True
    assert kw["encoding"] == "utf-8"


def test_exec_check_defaut_false():
    assert _exec().call_args.kwargs["check"] is False


def test_exec_kwargs_deviennent_arguments_cli():
    """Les kwargs (hors noms réservés) sont ajoutés en paires clé/valeur au CLI."""
    run = _exec("build", mode="rapide")
    assert run.call_args.args[0] == ["/bin/truc", "build", "mode", "rapide"]
    # ...et ne sont PAS passés à subprocess.run.
    assert "mode" not in run.call_args.kwargs


def test_exec_noms_reserves_ne_partent_pas_en_cli():
    """Un nom réservé (cwd/timeout/…) va à subprocess.run, pas dans la commande."""
    run = _exec("build", cwd="/x", timeout=5)
    assert run.call_args.args[0] == ["/bin/truc", "build"]  # cwd/timeout absents
    assert run.call_args.kwargs["cwd"] == "/x"
    assert run.call_args.kwargs["timeout"] == 5


def test_exec_timeout_propage_timeoutexpired():
    """À l'expiration, subprocess.TimeoutExpired remonte à l'appelant."""
    with patch("automatheque.util.dependances_externes.subprocess.run") as run:
        run.side_effect = subprocess.TimeoutExpired(cmd="truc", timeout=1)
        with pytest.raises(subprocess.TimeoutExpired):
            Executant("/bin/truc").exec(timeout=1)


# --- recup_executable / test d'exécution (#25) ------------------------------


def test_recup_executable_absent_renvoie_false(tmp_path):
    """Un nom introuvable et un chemin de repli inexistant → False."""
    assert recup_executable("nom-improbable-xyz", str(tmp_path / "absent")) is False


def test_recup_executable_sans_test_ne_lance_pas(tmp_path):
    """Par défaut : présence + bit exécutable suffisent, sans lancer le binaire."""
    faux = tmp_path / "faux"
    faux.write_text("ceci n'est pas un binaire")
    faux.chmod(0o755)
    # Accepté sur la seule base des permissions, sans tentative d'exécution.
    assert recup_executable("nom-improbable-xyz", str(faux)) == str(faux)


def test_recup_executable_teste_execution_detecte_non_binaire(tmp_path):
    """Avec ``teste_execution``, un faux exécutable (non binaire) est rejeté."""
    faux = tmp_path / "faux"
    faux.write_text("ceci n'est pas un binaire")
    faux.chmod(0o755)
    assert (
        recup_executable("nom-improbable-xyz", str(faux), teste_execution=True) is False
    )


def test_recup_executable_teste_execution_accepte_vrai_binaire():
    """Un exécutable qui démarre réellement (l'interpréteur Python) est accepté."""
    path = recup_executable("nom-improbable-xyz", sys.executable, teste_execution=True)
    assert path == sys.executable


def test_executable_fonctionne_vrai_sur_binaire():
    assert _executable_fonctionne(sys.executable) is True


def test_executable_fonctionne_faux_sur_inexistant():
    assert _executable_fonctionne("/chemin/qui/nexiste/pas/xyz") is False


def test_executable_fonctionne_timeout_considere_ok():
    """Un dépassement de délai signifie que le binaire *tournait* → True."""
    with patch("automatheque.util.dependances_externes.subprocess.run") as run:
        run.side_effect = subprocess.TimeoutExpired(cmd="x", timeout=2)
        assert _executable_fonctionne("/bin/peu-importe") is True
