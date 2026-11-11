import hashlib
import json
import sys
from pathlib import Path
import httpx
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import enrolled_refresh as refresh


async def test_enrolled_checks_are_independent_and_stage_only_reviewable_bytes(tmp_path, monkeypatch):
    base = "https://supabase.com/docs/"
    guides = [base + "guides/auth/" + s + ".md" for s in ("stable", "changed", "broken", "absent", "html")]
    sections = [base + "reference/cli/supabase-" + s for s in ("one", "two")]
    monkeypatch.setattr(refresh, "enrolled", lambda: set(guides + sections))
    stable = b"# Stable\n\nOld documentation"
    active = {s: hashlib.sha256(stable).hexdigest() for s in guides + sections if s != guides[3]}
    requests = []

    def handle(req):
        url = str(req.url)
        requests.append(url)
        if url == sections[0]:
            return httpx.Response(
                200,
                text='<section id="introduction"><h1>Supabase CLI</h1><p>Intro.</p></section><section id="supabase-one"><h2>supabase one</h2><p>Useful command.</p></section>',
            )
        if url == guides[2]:
            return httpx.Response(307, headers={"Location": "https://example.org/elsewhere"})
        if url == guides[4]:
            return httpx.Response(200, text="<html>Bad guide</html>")
        return httpx.Response(200, content=stable if url == guides[0] else b"# Changed\n\nNew docs")

    async with httpx.AsyncClient(transport=httpx.MockTransport(handle)) as client:
        outcomes = await refresh.stage_checks(client, active, tmp_path)
    assert outcomes == {"unchanged": 1, "changed": 2, "invalid": 2, "unreachable": 1, "not_indexed": 1}
    assert set(requests) == {*guides[:3], guides[4], sections[0]}
    receipt = next(tmp_path.glob("*/review.json"))
    result = json.loads(receipt.read_text())
    for url in (guides[1], sections[0]):
        item = result[url]
        assert item["accepted"] == active[url]
        assert (
            hashlib.sha256((receipt.parent / (item["observed"] + ".md")).read_bytes()).hexdigest()
            == item["observed"]
        )
    assert result[guides[3]] == {"status": "not_indexed"}


def test_enrollment_manifest_contains_only_distinct_official_documentation():
    urls = refresh.enrolled()
    assert len(urls) == 367
    assert sum(bool(refresh.SECTION_URL.fullmatch(u)) for u in urls) == 215


async def test_enrolled_only_never_calls_seed_or_embeddings(tmp_path, monkeypatch):
    import ingest_llms as ingest

    calls = []

    async def check(client, active, directory):
        calls.append((active, directory))
        return {"changed": 1, "unreachable": 1}

    monkeypatch.setattr(ingest, "RAW_DIR", tmp_path / "corpus")
    monkeypatch.setattr(ingest, "existing_hashes", lambda: {"url": ("hash", 1, None)})
    monkeypatch.setattr(ingest, "stage_checks", check)
    monkeypatch.setattr(
        ingest, "resolve_model", lambda *args: pytest.fail("model resolution in read-only check")
    )
    monkeypatch.setattr(sys, "argv", ["ingest_llms.py", "--enrolled-only"])
    assert await ingest.main() == 1
    assert calls == [({"url": "hash"}, tmp_path / "reference-review")]
