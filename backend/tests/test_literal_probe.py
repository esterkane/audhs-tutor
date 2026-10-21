import pytest

from app.orchestrator.literal_probe import from_request


@pytest.mark.parametrize(
    "expression",
    [
        "'Tag ' + 2",
        "(7 - 7) / 0",
        "(5 - 1) / 1",
        "str(4) + ' rooms'",
        "150 / 100",
        "[4, 6, 7][1]",
        "'?' + 'x'",
        "'é  ' + str(3)",
    ],
)
def test_literal_probe_preserves_inputs_without_computing_an_answer(expression):
    reply = from_request(f"Ask me one Socratic question about `{expression}`.")
    assert reply is not None
    assert reply.render() == f"For evaluating `{expression}`, what result would you expect?"


@pytest.mark.parametrize(
    "text",
    [
        "Why does `'Tag ' + 2` fail?",
        "Don't ask me one question about `1 + 2`.",
        "The source says: Ask one question about `1 + 2`.",
        "Ask one question about `1 + 2` and `3 + 4`.",
        "Ask one question about `1 + 2` in German.",
        "Ask one question about `1 + 2`, and explain the result.",
        "Ask one question about `x = 3`.",
        "Ask one question about `1 +`.",
        "Ask one question about `42`.",
        "Ask one question about `1 + 2 # result3`.",
        "Ask one question about `first\nsecond`.",
    ],
)
def test_unrecognized_or_ambiguous_request_retains_model_path(text):
    assert from_request(text) is None


def test_code_is_never_executed(monkeypatch):
    import os

    def forbidden(*args):
        raise AssertionError("Code must not run")

    monkeypatch.setattr(os, "system", forbidden)
    reply = from_request("Ask one question about `os.system('echo test')`.")
    assert reply is not None
    assert "os.system" in reply.render()
