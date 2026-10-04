"""Durable identity remains private and independent of process token rotation."""

from app.core import content_versions
from app.orchestrator.assessment_content import recovery_fingerprint


def test_recovery_identity_survives_token_rotation(monkeypatch):
    content = {"id": "a", "item_json": {"hidden_key": "private", "prompt": "Explain"}}
    original = recovery_fingerprint(content)
    public = content_versions.token(content)
    monkeypatch.setattr(content_versions, "_KEY", b"new process key")
    assert content_versions.token(content) != public
    assert recovery_fingerprint(content) == original
    assert "private" not in original
    assert recovery_fingerprint(dict(reversed(list(content.items())))) == original


def test_recovery_identity_changes_with_hidden_content():
    content = {"id": "a", "item_json": {"hidden_key": "first"}, "version": 1}
    assert recovery_fingerprint(content) != recovery_fingerprint(
        {**content, "item_json": {"hidden_key": "second"}}
    )
    assert recovery_fingerprint(content) != recovery_fingerprint({**content, "version": 2})
