"""Offline qualification for SDK method pages returned as HTML."""

import asyncio
import sys
from pathlib import Path

import httpx
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import ingest_llms as ing
from reference_html import reference_markdown

URL = "https://supabase.com/docs/reference/python/select"
PAGE = f"""<html><head><link rel="canonical" href="{URL}"></head><body>
<nav><h1>Not the article</h1>Unrelated menu</nav><h1>Python: select</h1>
<p>Read <a href="/docs/reference/python/eq">filters</a>.</p><h2>Examples</h2>
<pre><code class="language-python">query = (
    x &lt; 4
)
</code></pre><footer>Other APIs</footer></body></html>"""


def test_fetch_and_chunk_sdk_article_only(tmp_path, monkeypatch):
    monkeypatch.setattr(ing, "RAW_DIR", tmp_path)

    async def run():
        async with httpx.AsyncClient(
            transport=httpx.MockTransport(lambda _: httpx.Response(200, text=PAGE))
        ) as client:
            return await ing.fetch(client, ing.Doc(URL, 1, ing.product_of(URL)), asyncio.Semaphore(1))

    doc = asyncio.run(run())
    assert doc.product == "api" and doc.status == "active"
    assert "Unrelated menu" not in doc.text and "Other APIs" not in doc.text
    assert (
        "    x < 4\n)" in doc.text and "[filters](https://supabase.com/docs/reference/python/eq)" in doc.text
    )
    assert (tmp_path / (doc.hash + ".md")).read_text() == doc.text
    chunks = ing.chunk_markdown(doc.text, doc.product, URL)
    assert all(c.anchor is None for c in chunks)
    assert any(c.heading_path.endswith("Examples") and c.meta["has_code"] for c in chunks)


@pytest.mark.parametrize(
    "page", [PAGE.replace(URL, URL + "-other"), PAGE.split("</nav>")[0], PAGE.replace("</pre>", "")]
)
def test_reject_mismatched_or_incomplete(page):
    with pytest.raises(ValueError):
        reference_markdown(page, URL)


def test_discover_only_complete_methods_linked_by_selected_sdk():
    text = f"[Read]({URL}#examples) {URL}/subpage {URL}.md {URL} https://supabase.com/docs/reference/swift/select"
    seed = ing.Doc("https://supabase.com/llms/python.txt", 1, "api", text=text)
    assert ing.discover([seed]) == [URL]


def test_canonical_alias_refetched_before_storing(tmp_path, monkeypatch):
    monkeypatch.setattr(ing, "RAW_DIR", tmp_path)
    canonical = URL + "-new"
    calls = []

    def respond(request):
        calls.append(str(request.url))
        body = PAGE.replace(URL, canonical)
        if str(request.url) == URL:
            body = body.replace("Python: select", "Wrong alias text")
        return httpx.Response(200, text=body)

    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(respond)) as client:
            return await ing.fetch(client, ing.Doc(URL, 1, "api"), asyncio.Semaphore(1))

    doc = asyncio.run(run())
    assert calls == [URL, canonical] and doc.url == canonical and doc.status == "active"
    assert "Wrong alias text" not in doc.text

    directly_listed = ing.Doc(canonical, 1, "api", text=doc.text)
    assert [d.url for d in ing.canonical_documents([doc, directly_listed])] == [canonical]


def test_off_origin_redirect_cannot_supply_official_reference(tmp_path, monkeypatch):
    monkeypatch.setattr(ing, "RAW_DIR", tmp_path)

    def respond(request):
        if str(request.url) == URL:
            return httpx.Response(302, headers={"location": "https://example.org/other"})
        return httpx.Response(200, text=PAGE)

    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(respond)) as client:
            return await ing.fetch(client, ing.Doc(URL, 1, "api"), asyncio.Semaphore(1))

    assert asyncio.run(run()).status == "failed"
    assert not list(tmp_path.iterdir())


def test_historical_sdk_heading_and_edition_boundaries(tmp_path):
    historical = URL.replace("/select", "/v1/select")
    text = reference_markdown(PAGE.replace(URL, historical), historical)
    chunks = ing.chunk_markdown(text, "api", historical)
    assert all("python SDK v1" in c.heading_path for c in chunks)
    with pytest.raises(ValueError) as refused:
        reference_markdown(PAGE, historical)
    assert type(refused.value) is ValueError
    calls = []

    def respond(request):
        calls.append(str(request.url))
        if str(request.url) == historical:
            return httpx.Response(302, headers={"location": URL})
        return httpx.Response(200, text=PAGE)

    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(respond)) as client:
            return await ing.fetch(
                client, ing.Doc(historical, 1, "api"), asyncio.Semaphore(1), raw_dir=tmp_path
            )

    assert asyncio.run(run()).status == "failed"
    assert not list(tmp_path.iterdir())


@pytest.mark.parametrize(
    "family,product", [("api", "platform"), ("server", "api"), ("middleware", "api"), ("tanstack_db", "api")]
)
def test_product_article_requires_its_own_canonical_and_preserves_code(family, product):
    url = f"https://supabase.com/docs/reference/{family}/example"
    source = PAGE.replace(URL, url)
    assert ing.product_of(url) == product
    result = reference_markdown(source, url)
    assert "query = (\n    x < 4\n)" in result and "Unrelated menu" not in result
    with pytest.raises(ValueError):
        reference_markdown(source.replace(url, URL), url)


@pytest.mark.parametrize("url,identity", ing.CONFIG_GUIDES.items())
def test_configuration_guide_uses_article_and_preserves_code(tmp_path, url, identity):
    title, setting = identity
    html = f"""<link rel="canonical" href="{url}"><h1>Navigation</h1>
    <article id="sb-docs-guide-main-article"><header><h1><p>{title}</p></h1></header>
    <h2>{setting}</h2><pre><code><span class="linenumber">1</span>value = 17</code></pre>
    </article><div>Feedback panel</div>"""
    assert ing.canonical_md(url + ".md") == ing.canonical_md(url) == url
    async def run(body):
        async with httpx.AsyncClient(transport=httpx.MockTransport(lambda _: httpx.Response(200, text=body))) as client:
            return await ing.fetch(client, ing.Doc(url, 1, ing.product_of(url)), asyncio.Semaphore(1), raw_dir=tmp_path)
    doc = asyncio.run(run(html))
    assert doc.status == "active" and doc.url == url
    assert doc.text.startswith(f"# {title}\n") and "\nvalue = 17\n" in doc.text
    assert "Navigation" not in doc.text and "Feedback panel" not in doc.text
    assert (tmp_path / f"{doc.hash}.md").read_text() == doc.text
    for invalid in (html.replace(url, url + "-other"), html.replace(setting, "missing"), html.replace("</article>", "")):
        assert asyncio.run(run(invalid)).status == "failed"
    assert len(list(tmp_path.iterdir())) == 1


def test_config_chunks_only_cite_published_heading_links():
    url = "https://supabase.com/docs/guides/local-development/cli/config"
    text = f"""# Supabase CLI config
Introduction.
## Auth Config[#]({url}#auth-config)
### `auth.jwt_expiry`[#]({url}#auth.jwt_expiry)
Tokens are valid for the configured number of seconds.
### Other
Another setting.
"""
    chunks = ing.chunk_markdown(text, "local-development", "/docs/guides/local-development/cli/config")
    assert [chunk.anchor for chunk in chunks] == [None, "auth.jwt_expiry", None]
    assert chunks[1].heading_path == "Supabase CLI config > Auth Config > `auth.jwt_expiry`"
