from pathlib import Path
import json
import sqlite3
import sys

import httpx
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import import_reference_stage as importer
import stage_reference_sitemap as staging


async def test_verified_page_and_indentation_are_authoritative(tmp_path):
    url = "https://supabase.com/docs/reference/python/select"
    xml = f'<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"><url><loc>{url}</loc></url></urlset>'.encode()
    html = f'<head><link rel="canonical" href="{url}"></head><main><h1>Python select</h1><p>Preserve the block below.</p><pre><code>if ready:\n    select()</code></pre></main>'
    target = tmp_path / "stage"
    async with httpx.AsyncClient(
        transport=httpx.MockTransport(lambda _: httpx.Response(200, text=html))
    ) as client:
        assert await staging.stage(client, [url], target, xml) == 0
    docs, excluded = importer.read_stage(target)
    assert excluded == 0 and docs[url].product == "api" and docs[url].chunks[0].anchor is None
    passage_file = target / "passages.jsonl"
    row = json.loads(passage_file.read_text())
    assert "    select()" in row["content"]
    row["content"] = row["content"].replace("    select()", "select()")
    passage_file.write_text(json.dumps(row) + "\n")
    with pytest.raises(ValueError, match="Passage content"):
        importer.read_stage(target)


def test_cache_is_bound_to_model_digest_and_vector_bytes(tmp_path):
    cache = sqlite3.connect(tmp_path / "qwen.sqlite")
    importer.verify_cache_identity(cache, "a" * 64, create=True)
    with pytest.raises(ValueError, match="different manifest"):
        importer.verify_cache_identity(cache, "b" * 64)
    cache.execute("create table vectors(key text,data blob,sha256 text)")
    cache.execute("insert into vectors values(?,?,?)", ("key", bytes(importer.VECTOR.size), "wrong"))
    with pytest.raises(ValueError, match="Corrupt"):
        importer.stored_vector(cache, "key")


async def test_failed_final_digest_cannot_approve_partial_vectors(monkeypatch):
    cache = sqlite3.connect(":memory:")
    digest = "b" * 64

    async def fail():
        raise ConnectionError("digest unavailable")

    monkeypatch.setattr(importer, "local_model_digest", fail)
    with pytest.raises(ConnectionError):
        await importer.prepare_verified({}, cache, digest)
    with pytest.raises(ValueError):
        importer.verify_completed(cache, digest)


async def test_only_successfully_verified_cache_can_be_reused(monkeypatch):
    cache = sqlite3.connect(":memory:")
    digest = "a" * 64

    async def identity():
        return digest

    monkeypatch.setattr(importer, "local_model_digest", identity)
    assert await importer.prepare_verified({}, cache, digest) == 0
    importer.verify_completed(cache, digest)
    assert await importer.prepare_verified({}, cache, digest) == 0
    with cache:
        cache.execute("delete from completion")
    with pytest.raises(ValueError, match="not completed"):
        importer.verify_completed(cache, digest)
    with pytest.raises(ValueError, match="not completed"):
        await importer.prepare_verified({}, cache, digest)
