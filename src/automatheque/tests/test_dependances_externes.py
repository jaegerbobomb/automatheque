"""Tests de ``Executant.exec`` (options subprocess explicites, #66)."""

import subprocess
from unittest.mock import MagicMock, patch

import pytest
from automatheque.util.dependances_externes import Executant


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


def test_exec_kwargs_transmis_a_subprocess_pas_en_cli():
    """Les kwargs vont à subprocess.run (échappatoire), plus en arguments CLI."""
    run = _exec("arg", start_new_session=True)
    assert run.call_args.args[0] == ["/bin/truc", "arg"]  # aucun token en plus
    assert run.call_args.kwargs["start_new_session"] is True


def test_exec_timeout_propage_timeoutexpired():
    """À l'expiration, subprocess.TimeoutExpired remonte à l'appelant."""
    with patch("automatheque.util.dependances_externes.subprocess.run") as run:
        run.side_effect = subprocess.TimeoutExpired(cmd="truc", timeout=1)
        with pytest.raises(subprocess.TimeoutExpired):
            Executant("/bin/truc").exec(timeout=1)
