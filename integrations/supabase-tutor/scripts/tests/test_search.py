"""The local search CLI must query in the same vector space as the stored documents."""

import sys
from pathlib import Path
from unittest.mock import Mock

import httpx
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import search

from backend.tutor.embedding_space import NOMIC, QWEN, QWEN_QUERY


@pytest.mark.parametrize(("model", "prefix"), [(NOMIC, "search_query: "), (QWEN, QWEN_QUERY)])
def test_query_uses_recorded_model(monkeypatch, model, prefix):
    monkeypatch.delenv("EMBEDDINGS_MODEL", raising=False)
    monkeypatch.setenv("EMBEDDINGS_PROVIDER", "ollama")
    conn = Mock()
    conn.execute.return_value.fetchall.return_value = [(model,)]
    response = httpx.Response(200, json={"embeddings": [[0.0] * 768]}, request=httpx.Request("POST", "http://localhost"))
    post = Mock(return_value=response)
    monkeypatch.setattr(search.httpx, "post", post)
    assert len(search.embed_query("setting", conn)) == 768
    payload = post.call_args.kwargs["json"]
    assert payload["model"] == model and payload["input"] == [prefix + "setting"]
    if model == QWEN:
        assert payload["dimensions"] == 768 and payload["truncate"] is False


def test_query_refuses_incompatible_model_before_embedding(monkeypatch):
    monkeypatch.setenv("EMBEDDINGS_PROVIDER", "ollama")
    monkeypatch.setenv("EMBEDDINGS_MODEL", NOMIC)
    conn = Mock()
    conn.execute.return_value.fetchall.return_value = [(QWEN,)]
    post = Mock()
    monkeypatch.setattr(search.httpx, "post", post)
    with pytest.raises(ValueError, match="incompatible"):
        search.embed_query("setting", conn)
    post.assert_not_called()
