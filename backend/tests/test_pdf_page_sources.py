import io
from uuid import uuid4

from pypdf import PdfWriter
from sqlalchemy import select

from app.db.models import Chunk, DocumentVersion
from app.knowledge.pdf_page_sources import read
from tests.pdf_scan_fixture import native_pdf, scanned_pdf
from tests.test_knowledge_authoring import complete
from tests.test_pdf_ocr import runtime


@runtime
async def test_mixed_pdf_pages_and_previous_transcription_remain_bound_to_saved_material(
    client, db, settings, tmp_path, monkeypatch
):
    settings.knowledge_authoring_root = str(tmp_path / "private")
    writer = PdfWriter()
    writer.append(io.BytesIO(native_pdf("The native introduction is on the first page.")))
    writer.append(io.BytesIO(scanned_pdf(tmp_path)))
    output = io.BytesIO()
    writer.write(output)
    raw = output.getvalue()

    async def upload():
        response = await client.post(
            "/api/knowledge-material/uploads", content=raw, headers={"X-Filename": "mixed.pdf"}
        )
        assert response.status_code == 200, response.text
        return response.json()

    first = await upload()
    base = "/api/knowledge-material/uploads/" + first["document_id"] + "/versions/"

    async def pages(version):
        r = await client.get(base + version + "/pages")
        assert r.status_code == 200, r.text
        return r.json()["pages"]

    old = await pages(first["document_version_id"])
    assert [(p["page"], p["ocr"]) for p in old] == [(1, False), (2, True)]
    assert "\n\n".join(p["text"] for p in old) == first["text"]
    preview_url = base + first["document_version_id"] + "/pages/2/preview"
    preview = await client.get(preview_url)
    assert preview.status_code == 200 and preview.content.startswith(b"\x89PNG\r\n\x1a\n")
    assert preview.headers["cache-control"] == "private, no-store"
    assert preview.headers["x-content-type-options"] == "nosniff"
    assert (await client.get(preview_url.replace("/2/preview", "/3/preview"))).status_code == 404
    assert (await client.get(base + "wrong/pages/2/preview")).status_code == 404
    quote = "Datenbankrechte und Zeilenfilter"
    assert quote not in old[0]["text"] and quote in old[1]["text"]
    monkeypatch.setattr(
        "app.knowledge.ingest.pdf.ocr_pages",
        lambda data, pages, opts: {p: "Different transcription." for p in pages},
    )
    second = await upload()
    assert (
        first["document_id"] == second["document_id"]
        and first["document_version_id"] != second["document_version_id"]
    )
    assert await pages(first["document_version_id"]) == old
    assert (await pages(second["document_version_id"]))[1]["text"] == "Different transcription."
    form = complete(upload_id=first["document_id"], upload_version_id=first["document_version_id"])
    form["notes"] = first["text"]
    created = await client.post(
        "/api/knowledge-material/drafts", json=form, headers={"Idempotency-Key": str(uuid4())}
    )
    assert created.status_code == 200, created.text
    draft = created.json()
    ids = draft["payload"]["learning_objects"][0]["sources"]
    chunks = (await db.scalars(select(Chunk).where(Chunk.id.in_(ids)))).all()
    assert chunks and {chunk.document_version_id for chunk in chunks} == {
        first["document_version_id"]
    }
    scanned = next(chunk for chunk in chunks if quote in chunk.text)
    response = await client.get("/api/curriculum/chunks/" + scanned.id)
    assert response.status_code == 200, response.text
    passage = response.json()
    assert passage["pdf_page"] == 2 and "p. 2" in passage["citation"]
    assert passage["open_url"].endswith("#page=2")
    wrong = await client.get(base + "wrong/pages")
    assert wrong.status_code == 404
    # Lack of page-level evidence never guesses from a chunk's words or its ordinal.
    version = await db.get(DocumentVersion, first["document_version_id"])
    audit = next((tmp_path / "private").rglob("*" + version.content_hash + ".json"))
    audit.unlink()
    assert await pages(first["document_version_id"]) == []
    source = next((tmp_path / "private").rglob("*.pdf"))
    assert not read(source, tmp_path / "other-owner", version.content_hash).pages
    assert (await client.get(preview_url)).status_code == 404
    latest_preview = base + second["document_version_id"] + "/pages/2/preview"
    assert (await client.get(latest_preview)).content == preview.content
    source.write_bytes(native_pdf("A different file must not be shown."))
    assert (await client.get(latest_preview)).status_code == 404


@runtime
async def test_unreadable_scan_remains_selectable_between_readable_pages(
    client, settings, tmp_path, monkeypatch
):
    settings.knowledge_authoring_root = str(tmp_path / "private")
    writer = PdfWriter()
    writer.append(io.BytesIO(native_pdf("Readable first page.")))
    writer.append(io.BytesIO(scanned_pdf(tmp_path)))
    writer.append(io.BytesIO(native_pdf("Readable last page.")))
    raw = io.BytesIO()
    writer.write(raw)
    monkeypatch.setattr(
        "app.knowledge.ingest.pdf.ocr_pages", lambda _, pages, opts: {p: "" for p in pages}
    )
    res = await client.post(
        "/api/knowledge-material/uploads",
        content=raw.getvalue(),
        headers={"X-Filename": "mixed.pdf"},
    )
    assert res.status_code == 200, res.text
    upload = res.json()
    response = await client.get(
        f"/api/knowledge-material/uploads/{upload['document_id']}/versions/{upload['document_version_id']}/pages"
    )
    assert response.status_code == 200
    pages = response.json()["pages"]
    assert [p["page"] for p in pages] == [1, 2, 3]
    assert pages[1] == {"page": 2, "ocr": True, "text": ""}
    assert upload["text"] == "\n\n".join(p["text"] for p in pages if p["text"])
