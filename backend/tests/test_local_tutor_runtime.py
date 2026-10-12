import importlib.util
from pathlib import Path
from unittest.mock import Mock

import pytest

spec = importlib.util.spec_from_file_location(
    "local_tutor_runtime", Path(__file__).resolve().parents[2] / "scripts/local_tutor_runtime.py"
)
assert spec and spec.loader
runtime = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runtime)


def test_profile_is_local_explicit_and_does_not_use_normal_port():
    for port in [0, 80, 11434, 65536]:
        with pytest.raises(ValueError):
            runtime.environment(port, False)
    base = runtime.environment(11435, False)
    assert base["OLLAMA_HOST"] == "127.0.0.1:11435"
    assert base["OLLAMA_NO_CLOUD"] == "1"
    assert base["OLLAMA_MAX_LOADED_MODELS"] == "2"
    assert base["LLAMA_ARG_SWA_FULL"] == "0"
    assert runtime.environment(11435, True)["LLAMA_ARG_SWA_FULL"] == "1"


def test_ctrl_c_stops_only_owned_process_group(monkeypatch):
    process = Mock(pid=12345)
    process.wait.side_effect = [KeyboardInterrupt(), 0]
    process.poll.return_value = None
    popen = Mock(return_value=process)
    kill = Mock()
    monkeypatch.setattr(runtime.subprocess, "Popen", popen)
    monkeypatch.setattr(runtime.os, "killpg", kill)
    assert runtime.serve(Path("/fake/ollama"), runtime.environment(11435, True)) == 130
    assert popen.call_args.kwargs["start_new_session"] is True
    kill.assert_called_once_with(12345, runtime.signal.SIGTERM)


def test_unsupported_runner_rejected(tmp_path, monkeypatch):
    runner = tmp_path / "llama-server"
    runner.touch()
    monkeypatch.setattr(
        runtime.subprocess,
        "run",
        Mock(return_value=Mock(returncode=0, stdout="Other flags", stderr="")),
    )
    with pytest.raises(ValueError, match="does not advertise"):
        runtime.check_runner(tmp_path / "ollama")


def test_sigterm_routes_to_owned_cleanup_and_restores_handler(monkeypatch):
    previous = runtime.signal.getsignal(runtime.signal.SIGTERM)
    process = Mock(pid=12345)
    process.poll.return_value = None
    calls = []

    def wait(*args, **kwargs):
        calls.append(1)
        if len(calls) == 1:
            runtime.signal.getsignal(runtime.signal.SIGTERM)(runtime.signal.SIGTERM, None)
        return 0

    process.wait.side_effect = wait
    kill = Mock()
    monkeypatch.setattr(runtime.subprocess, "Popen", Mock(return_value=process))
    monkeypatch.setattr(runtime.os, "killpg", kill)
    assert runtime.serve(Path("/fake/ollama"), runtime.environment(11435, True)) == 130
    kill.assert_called_once_with(12345, runtime.signal.SIGTERM)
    assert runtime.signal.getsignal(runtime.signal.SIGTERM) == previous
