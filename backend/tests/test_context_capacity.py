from types import SimpleNamespace

import pytest

from app.models_ai import context_capacity as capacity
from app.models_ai.provider import Message


@pytest.mark.parametrize(
    ("length", "output", "expected"),
    [
        (2000, 1600, 8192),
        (7000, 1600, 16384),
        (2000, 10000, 16384),
    ],
)
def test_capacity_keeps_all_content_and_full_output(
    tmp_path, monkeypatch, length, output, expected
):
    path = tmp_path / "tokenizer.json"
    path.write_text("fixture")
    seen = []

    class Counter:
        def encode(self, text, add_special_tokens):
            assert add_special_tokens is False
            seen.append(text)
            return SimpleNamespace(ids=list(range(len(text))))

    monkeypatch.setattr(capacity, "_load", lambda *args: Counter())
    text = "α" * length
    assert (
        capacity.context_capacity(16384, [Message(role="user", content=text)], output, str(path))
        == expected
    )
    assert seen == [text]


def test_unknown_missing_or_corrupt_tokenizer_retains_capacity(tmp_path):
    messages = [Message(role="user", content="An unchanged question")]
    assert capacity.context_capacity(16384, messages, 1600, None) == 16384
    assert capacity.context_capacity(16384, messages, 1600, str(tmp_path / "absent")) == 16384
    path = tmp_path / "bad.json"
    path.write_text("invalid tokenizer")
    assert capacity.context_capacity(16384, messages, 1600, str(path)) == 16384
    assert capacity.context_capacity(4096, messages, 1600, str(path)) == 4096
