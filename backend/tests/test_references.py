import pytest
from sqlalchemy import func, select

from app.core.errors import AppError
from app.db.models import ChunkProvenance, Document, Session
from app.knowledge import reference_fetch, references

HTML = (
    b"<html><head><title>Synthetic reference</title></head><body><h1>Arrays</h1>"
    b"<p>Arrays have shapes.</p><script>secret()</script>"
    b"<footer>Copyright notice</footer></body></html>"
)


@pytest.fixture
async def fetched(monkeypatch):
    calls = []

    async def fake(url):
        calls.append(url)
        return reference_fetch.FetchedPage(HTML, "text/html")

    monkeypatch.setattr(reference_fetch, "fetch", fake)
    return calls


async def test_explicit_load_cache_and_hash_validation(tmp_path, fetched):
    assert references.current(tmp_path, "numpy-basics") is None
    assert not fetched
    copy = await references.load(tmp_path, "numpy-basics")
    assert fetched == [references.CATALOG["numpy-basics"].url]
    assert "Arrays have shapes." in copy.text_preview and "secret()" not in copy.text_preview
    assert copy.origin == "third_party"
    assert await references.load(tmp_path, "numpy-basics") == copy
    assert len(fetched) == 1
    file = tmp_path / "numpy-basics" / f"{copy.snapshot_id}.json"
    assert "Copyright notice" in file.read_text()
    file.write_text(file.read_text().replace("Arrays have shapes.", "changed"))
    with pytest.raises(AppError, match="unavailable or changed"):
        references.current(tmp_path, "numpy-basics")
    assert len(fetched) == 1


async def test_failed_refresh_preserves_previous_copy(tmp_path, fetched, monkeypatch):
    copy = await references.load(tmp_path, "numpy-basics")

    async def broken(url):
        raise AppError("offline", "offline", 502)

    monkeypatch.setattr(reference_fetch, "fetch", broken)
    with pytest.raises(AppError):
        await references.load(tmp_path, "numpy-basics", refresh=True)
    assert references.current(tmp_path, "numpy-basics") == copy


async def test_explicit_import_is_local_idempotent_and_does_not_create_session(
    db, tmp_path, fetched, fake_repo
):
    copy = await references.load(tmp_path, "numpy-basics")
    assert await db.scalar(select(func.count()).select_from(Document)) == 0
    repo = fake_repo
    first = await references.import_copy(db, repo, tmp_path, "numpy-basics", copy.snapshot_id)
    second = await references.import_copy(db, repo, tmp_path, "numpy-basics", copy.snapshot_id)
    assert first.document_id == second.document_id and not second.changed
    assert len(fetched) == 1
    assert (await db.get(Document, first.document_id)).uri == copy.url
    assert all(row.trust_tier == 1 for row in await db.scalars(select(ChunkProvenance)))
    assert await db.scalar(select(func.count()).select_from(Session)) == 0


async def test_index_failure_keeps_copy(db, tmp_path, fetched, monkeypatch, fake_repo):
    copy = await references.load(tmp_path, "numpy-basics")

    async def fail(*a, **kw):
        raise RuntimeError("index unavailable")

    monkeypatch.setattr(references, "ingest_source", fail)
    with pytest.raises(AppError, match="reading copy is kept"):
        await references.import_copy(db, fake_repo, tmp_path, "numpy-basics", copy.snapshot_id)
    assert references.current(tmp_path, "numpy-basics") == copy


async def test_http_has_no_arbitrary_url_or_implicit_download(client, settings, tmp_path, fetched):
    settings.reference_cache_dir = str(tmp_path)
    status = await client.get("/api/references/numpy-basics")
    assert status.status_code == 200 and status.json()["snapshot"] is None
    assert not fetched
    assert (await client.post("/api/references/not-a-card/load", json={})).status_code == 404
    assert (
        await client.post("/api/references/numpy-basics/load", json={"url": "http://localhost"})
    ).status_code == 422
    loaded = await client.post("/api/references/numpy-basics/load", json={})
    assert loaded.status_code == 200, loaded.text
    assert len(fetched) == 1
    assert (await client.get("/api/references/numpy-basics")).json()["snapshot"][
        "snapshot_id"
    ] == loaded.json()["snapshot_id"]
    assert len(fetched) == 1
