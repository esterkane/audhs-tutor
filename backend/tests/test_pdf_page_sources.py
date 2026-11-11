import io
from uuid import uuid4

import pytest
from pypdf import PdfWriter
from sqlalchemy import select

from app.db.models import Chunk, DocumentVersion, SkillNode
from app.knowledge.pdf_page_sources import read
from tests.pdf_scan_fixture import diagram_pdf, native_pdf, scanned_pdf, vector_pdf
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
    activated = await client.post(
        f"/api/curriculum/drafts/{draft['id']}/publish", json={"expected_version": draft["version"]}
    )
    assert activated.is_success, activated.text
    skill = await db.scalar(select(SkillNode))
    reading = await client.get(f"/api/knowledge-material/skills/{skill.id}/reading")
    assert reading.json()["original_pdf"] == {
        "upload_id": first["document_id"],
        "version_id": first["document_version_id"],
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


@runtime
async def test_diagram_without_recognized_words_has_original_but_no_chunks(
    client, db, settings, tmp_path
):
    settings.knowledge_authoring_root = str(tmp_path / "private")
    raw = diagram_pdf()
    res = await client.post(
        "/api/knowledge-material/uploads", content=raw, headers={"X-Filename": "figure.pdf"}
    )
    assert res.status_code == 200, res.text
    data = res.json()
    assert data["text"] == "" and data["characters"] == 0 and data["ocr_empty_pages"] == [1]
    assert (
        list(
            await db.scalars(
                select(Chunk).where(Chunk.document_version_id == data["document_version_id"])
            )
        )
        == []
    )
    assert next((tmp_path / "private").rglob("*.pdf")).read_bytes() == raw
    pages = f"/api/knowledge-material/uploads/{data['document_id']}/versions/{data['document_version_id']}/pages"
    assert (await client.get(pages)).json()["pages"] == [{"page": 1, "ocr": True, "text": ""}]
    preview = await client.get(pages + "/1/preview")
    assert preview.status_code == 200 and preview.content.startswith(b"\x89PNG")
    assert not (
        await client.post("/api/knowledge-material/drafts", json={"title": "Figure", "notes": ""})
    ).is_success


@pytest.mark.parametrize(
    ("filename", "content", "error"),
    [
        ("empty.pdf", b"", "empty_upload"),
        ("bad.pdf", b"XYZ", "unreadable_upload"),
        ("empty.txt", b"  ", "empty_upload"),
    ],
)
async def test_unusable_files_still_fail(client, filename, content, error):
    res = await client.post(
        "/api/knowledge-material/uploads", content=content, headers={"X-Filename": filename}
    )
    assert res.status_code == 422 and res.json()["error"]["code"] == error


@runtime
@pytest.mark.parametrize("mixed", [False, True])
async def test_native_vector_artwork_counts_only_visible_pages(
    client, db, settings, tmp_path, mixed
):
    settings.knowledge_authoring_root = str(tmp_path / "uploads")
    writer = PdfWriter()
    writer.append(io.BytesIO(vector_pdf()))
    writer.append(io.BytesIO(vector_pdf(b"1 1 1 rg 80 40 200 80 re f")))
    writer.append(io.BytesIO(vector_pdf(b"0.996 0.996 0.996 rg 80 40 200 80 re f")))
    if mixed:
        writer.append(io.BytesIO(native_pdf("An independent caption.")))
    stream = io.BytesIO()
    writer.write(stream)
    res = await client.post(
        "/api/knowledge-material/uploads",
        content=stream.getvalue(),
        headers={"X-Filename": "drawing.pdf"},
    )
    assert res.status_code == 200, res.text
    data = res.json()
    assert data["text"] == ("An independent caption." if mixed else "")
    assert data["ocr_pages"] == [] and data["ocr_empty_pages"] == []
    base = f"/api/knowledge-material/uploads/{data['document_id']}/versions/{data['document_version_id']}/pages"
    pages = (await client.get(base)).json()["pages"]
    assert [p["page"] for p in pages] == ([1, 3, 4] if mixed else [1, 3])
    assert all(p == {"page": p["page"], "text": "", "ocr": False} for p in pages[:2])
    assert (await client.get(base + "/1/preview")).status_code == 200
    assert (await client.get(base + "/2/preview")).status_code == 404
    chunks = list(
        await db.scalars(
            select(Chunk).where(Chunk.document_version_id == data["document_version_id"])
        )
    )
    assert len(chunks) == int(mixed)


@runtime
@pytest.mark.parametrize(
    "raw",
    [
        vector_pdf(b""),
        vector_pdf(b"1 1 1 rg 80 40 200 80 re f"),
        vector_pdf(b"0 0 1 rg 800 400 200 80 re f"),
        diagram_pdf(blank=True),
    ],
)
async def test_visibly_blank_pdf_still_rejected(client, settings, tmp_path, raw):
    settings.knowledge_authoring_root = str(tmp_path / "uploads")
    res = await client.post(
        "/api/knowledge-material/uploads", content=raw, headers={"X-Filename": "blank.pdf"}
    )
    assert res.status_code == 422 and res.json()["error"]["code"] == "empty_upload"
