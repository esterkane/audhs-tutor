import json
import sqlite3
import sys
from pathlib import Path

import httpx
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from postgres_manual_article import ManualArticle
from postgres_manual_refresh import ORIGIN, audit, digest


def page(slug, code="SELECT 'a  b'", header="Old", anchor="x", href="types.html"):
    return f"""<p>{header}</p><a class="docs-version-selected" href="/docs/17/{slug}">17</a>
<div id="docContent"><div class="navheader"><p>{header}</p></div><div class="sect1" id="{anchor}"><p>See <a href="{href}">types</a></p><pre>{code}</pre></div><div class="navfooter"><p>{header}</p></div></div>""".encode()


def test_article_keeps_code_boundaries_and_citation_targets():
    url = ORIGIN + "sample.html"

    def fp(**args):
        return ManualArticle.parse(url, page("sample.html", **args)).fingerprint

    assert fp(header="New") == fp()
    assert len({fp(), fp(code="SELECT 'a b'"), fp(anchor="new-x"), fp(href="old-types.html")}) == 4
    with pytest.raises(ValueError):
        ManualArticle.parse(url, page("other.html"))
    raw = page("sample.html")
    with pytest.raises(ValueError):
        ManualArticle.parse(url, raw.replace(b'id="docContent"', b'id="unrelated"'))


async def test_rotates_and_keeps_originals_on_change_redirect_or_invalid_response(tmp_path):
    rows = {}
    bodies = {}
    originals = tmp_path / "original"
    originals.mkdir()
    state = tmp_path / "state"
    for name in ["a.html", "b.html", "c.html", "d.html", "e.html"]:
        raw = page(name)
        h = digest(raw)
        (originals / (h + ".html")).write_bytes(raw)
        rows[ORIGIN + name] = h
        bodies[ORIGIN + name] = raw
    bodies[ORIGIN + "a.html"] = page("a.html", header="recent announcement")
    bodies[ORIGIN + "b.html"] = page("b.html", code="SELECT 'a b'")
    bodies[ORIGIN + "d.html"] = page("wrong.html")
    (originals / (rows[ORIGIN + "e.html"] + ".html")).write_bytes(b"corrupt")
    calls = []

    def fetch(req):
        url = str(req.url)
        calls.append(url)
        if url.endswith("c.html"):
            return httpx.Response(302, headers={"Location": "https://www.postgresql.org/docs/current/c.html"})
        return httpx.Response(200, content=bodies[url])

    async with httpx.AsyncClient(transport=httpx.MockTransport(fetch)) as client:
        assert await audit(client, rows, originals, state, 2) == {"site_only": 1, "article_changed": 1}
        assert await audit(client, rows, originals, state, 3) == {
            "unreachable": 1,
            "invalid_article": 1,
            "invalid_baseline": 1,
        }
    assert len(calls) == len(set(calls)) == 4
    assert list((state / "candidates").glob("*.html"))[0].read_bytes() == bodies[ORIGIN + "b.html"]
    assert (originals / (rows[ORIGIN + "b.html"] + ".html")).read_bytes() == page("b.html")
    with sqlite3.connect(state / "checks.sqlite") as db:
        assert len(db.execute("select url from checks").fetchall()) == 5
        saved = json.loads(
            db.execute("select result from checks where url=?", (ORIGIN + "b.html",)).fetchone()[0]
        )
        assert saved["old_article"] != saved["new_article"]
