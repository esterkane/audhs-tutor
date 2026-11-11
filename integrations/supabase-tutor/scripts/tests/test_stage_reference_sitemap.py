from pathlib import Path
import json
import sys

import httpx
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import stage_reference_sitemap as sdk

BASE = "https://supabase.com/docs/reference/"
CURRENT = BASE + "javascript/select"
OLD = BASE + "javascript/v1/select"


def test_inventory_preserves_sdk_versions_and_counts_unhandled_families():
    urls = [
        CURRENT,
        OLD,
        CURRENT + "/",
        BASE + "api/get",
        BASE + "javascript/v1/extra/path",
        "https://untrusted.example/docs/reference/javascript/select",
        CURRENT + "?other=1",
        BASE + "not_a_sdk/get",
    ]
    raw = (
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
        + "".join("<url><loc>" + url + "</loc></url>" for url in urls)
        + "</urlset>"
    ).encode()
    pages = sdk.inventory(raw)
    assert pages == {
        CURRENT: ("javascript", "unversioned"),
        OLD: ("javascript", "v1"),
        BASE + "api/get": ("api", "product"),
        BASE + "javascript/v1/extra/path": ("javascript", "unsupported"),
        BASE + "not_a_sdk/get": ("not_a_sdk", "unsupported"),
    }
    assert sdk.choose(pages, None, None, None, "product") == [BASE + "api/get"]
    assert sdk.choose(pages, "javascript", "v1", 1) == [OLD]
    assert set(sdk.choose(pages, None, None, 1)) == {CURRENT, OLD}
    with pytest.raises(ValueError):
        sdk.inventory(b"<sitemapindex/>")


async def test_stage_deduplicates_canonical_targets_and_preserves_failures(tmp_path):
    alias = BASE + "javascript/alias"

    def respond(request):
        url = str(request.url)
        if url == OLD:
            return httpx.Response(503)
        return httpx.Response(
            200,
            text=f'<html><head><link rel="canonical" href="{CURRENT}"></head><body><main><article><h1>JavaScript: select</h1><p>A precise synthetic SDK explanation for citation.</p></article></main></body></html>',
        )

    folder = tmp_path / "fixture"
    async with httpx.AsyncClient(transport=httpx.MockTransport(respond)) as client:
        assert await sdk.stage(client, [alias, CURRENT, OLD], folder, b"manifest") == 1
        with pytest.raises(FileExistsError):
            await sdk.stage(client, [CURRENT], folder, b"another-manifest")
    rows = [json.loads(s) for s in (folder / "sources.jsonl").read_text().splitlines()]
    assert [(s["requested_url"], s["status"]) for s in rows] == [
        (alias, "staged"),
        (CURRENT, "staged"),
        (OLD, "failed"),
    ]
    assert rows[0]["canonical_url"] == rows[1]["canonical_url"] == CURRENT
    assert len(list((folder / "pages").glob("*.md"))) == 1
    passages = [json.loads(s) for s in (folder / "passages.jsonl").read_text().splitlines()]
    assert len(passages) == 1 and passages[0]["url"] == CURRENT and passages[0]["edition"] == "unversioned"
    assert json.loads((folder / "summary.json").read_text())["canonical_staged"] == 1


async def test_heading_only_canonical_has_no_passages(tmp_path):
    url = BASE + "server/types-allow"
    html = f'<html><head><link rel="canonical" href="{url}"></head><body><nav>Sidebar with text.</nav><h1>Allow</h1></body></html>'
    async with httpx.AsyncClient(
        transport=httpx.MockTransport(lambda _: httpx.Response(200, text=html))
    ) as client:
        target = tmp_path / "empty-article"
        assert await sdk.stage(client, [url], target, b"fixture") == 1
    row = json.loads((target / "sources.jsonl").read_text())
    assert row["requested_url"] == url and row["status"] == "no_indexable_body"
    assert (target / "passages.jsonl").read_text() == ""
