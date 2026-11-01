import hashlib
import io
import shutil
import subprocess
from pathlib import Path

import pytest
from httpx import AsyncClient
from pypdf import PdfReader

from app.core.config import Settings
from app.knowledge.ingest import pdf_ocr
from app.knowledge.ingest.loaders import load_file
from app.knowledge.ingest.pdf import pdf_blocks
from app.knowledge.ingest.pdf_ocr import PdfOcrError, PdfOcrLimit, PdfOcrOptions, PdfOcrUnavailable
from tests.pdf_scan_fixture import native_pdf, scanned_pdf

runtime = pytest.mark.skipif(
    not shutil.which("pdftoppm") or not shutil.which("tesseract"),
    reason="local OCR binaries not installed",
)


def test_native_pdf_does_not_invoke_ocr(monkeypatch):
    monkeypatch.setattr(
        "app.knowledge.ingest.pdf.ocr_pages", lambda *a: pytest.fail("Native text must not run OCR")
    )
    assert "Table privileges" in pdf_blocks(native_pdf(), ocr=PdfOcrOptions())[0].text


@runtime
def test_real_mixed_pdf_preserves_native_pages_and_recognizes_scan(tmp_path):
    data = scanned_pdf(tmp_path, mixed=True)
    path = tmp_path / "mixed.pdf"
    path.write_bytes(data)
    document = load_file(path, pdf_ocr=PdfOcrOptions())
    assert document.blocks[0].text == pdf_blocks(native_pdf())[0].text
    assert [b.heading for b in document.blocks] == ["p. 1", "p. 2"]
    assert "Table privileges and row policies are separate" in document.blocks[1].text
    assert "Datenbankrechte und Zeilenfilter" in document.blocks[1].text
    assert document.meta["pdf_extraction"]["ocr_pages"] == [2]
    assert document.meta["pdf_extraction"]["languages"] == "eng+deu"
    assert path.read_bytes() == data


@runtime
async def test_real_scanned_upload_is_usable_source(
    client: AsyncClient, settings: Settings, tmp_path: Path
):
    settings.knowledge_authoring_root = str(tmp_path / "private")
    data = scanned_pdf(tmp_path)
    response = await client.post(
        "/api/knowledge-material/uploads",
        content=data,
        headers={"X-Filename": "scanned-reference.pdf"},
    )
    assert response.status_code == 200, response.text
    result = response.json()
    assert result["ocr_pages"] == [1]
    assert "Table privileges and row policies are separate" in result["text"]
    assert result["sha256"] == hashlib.sha256(data).hexdigest()
    assert list((tmp_path / "private").rglob("*.pdf"))[0].read_bytes() == data


@runtime
async def test_disabled_ocr_does_not_silently_drop_scanned_pages(
    client: AsyncClient, settings: Settings, tmp_path: Path
):
    settings.knowledge_authoring_root = str(tmp_path / "private")
    settings.pdf_ocr_enabled = False
    data = scanned_pdf(tmp_path, mixed=True)
    response = await client.post(
        "/api/knowledge-material/uploads", content=data, headers={"X-Filename": "mixed.pdf"}
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "pdf_ocr_unavailable"


def test_missing_binaries_has_actionable_error(monkeypatch):
    monkeypatch.setattr(pdf_ocr.shutil, "which", lambda name: None)
    with pytest.raises(PdfOcrUnavailable):
        pdf_ocr.ocr_pages(b"%PDF", [1], PdfOcrOptions())


def test_page_limit_checked_before_subprocess(monkeypatch):
    monkeypatch.setattr(
        pdf_ocr.subprocess, "run", lambda *a, **k: pytest.fail("Limit must be checked first")
    )
    with pytest.raises(PdfOcrLimit):
        pdf_ocr.ocr_pages(b"%PDF", [1, 2], PdfOcrOptions(max_pages=1))


@pytest.mark.parametrize(
    "failure", [subprocess.TimeoutExpired("ocr", 1), subprocess.CalledProcessError(1, "ocr")]
)
def test_runtime_failure_does_not_return_partial_text(monkeypatch, failure):
    monkeypatch.setattr(pdf_ocr.shutil, "which", lambda name: "/usr/bin/" + name)

    def fail(*a, **k):
        raise failure

    monkeypatch.setattr(pdf_ocr.subprocess, "run", fail)
    with pytest.raises(PdfOcrError):
        pdf_ocr.ocr_pages(b"%PDF", [1], PdfOcrOptions())


def test_missing_language_pack(monkeypatch):
    monkeypatch.setattr(pdf_ocr.shutil, "which", lambda name: "/usr/bin/" + name)
    monkeypatch.setattr(
        pdf_ocr.subprocess,
        "run",
        lambda *a, **k: subprocess.CompletedProcess(
            a[0], 0, b"List of available languages:\neng\n", b""
        ),
    )
    with pytest.raises(PdfOcrUnavailable):
        pdf_ocr.ocr_pages(b"%PDF", [1], PdfOcrOptions())


def test_selectable_header_survives_ocr_and_counts_as_scanned_page(monkeypatch):
    import app.knowledge.ingest.pdf as loader

    # A header is selectable but the body is an image; do not silently keep just the header.
    monkeypatch.setattr(loader, "_has_image", lambda resources: True)
    monkeypatch.setattr(loader, "ocr_pages", lambda data, pages, opts: {1: "Recognized image body"})
    from pypdf import PdfWriter
    from pypdf.generic import DecodedStreamObject, NameObject

    writer = PdfWriter()
    writer.add_page(PdfReader(io.BytesIO(native_pdf())).pages[0])
    content = DecodedStreamObject()
    content.set_data(b"BT /F1 16 Tf 40 720 Td (Selectable page header) Tj ET")
    writer.pages[0][NameObject("/Contents")] = writer._add_object(content)
    buffer = io.BytesIO()
    writer.write(buffer)
    extraction = {}
    blocks = loader.pdf_blocks(buffer.getvalue(), ocr=PdfOcrOptions(), extraction=extraction)
    assert "Selectable page header" in blocks[0].text
    assert "Recognized image body" in blocks[0].text
    assert extraction["ocr_pages"] == [1]


@runtime
async def test_changed_ocr_retains_previous_source_version(
    client, db, settings, tmp_path, monkeypatch
):
    from sqlalchemy import select

    from app.db.models import Chunk, DocumentVersion

    settings.knowledge_authoring_root = str(tmp_path / "private")
    data = scanned_pdf(tmp_path)
    first = await client.post(
        "/api/knowledge-material/uploads", content=data, headers={"X-Filename": "scan.pdf"}
    )
    assert first.status_code == 200
    source = first.json()
    original = await db.scalar(
        select(DocumentVersion).where(DocumentVersion.document_id == source["document_id"])
    )
    original_hash = original.content_hash
    monkeypatch.setattr(
        "app.knowledge.ingest.pdf.ocr_pages",
        lambda data, pages, opts: {
            p: "Changed extraction: preserve previous source evidence." for p in pages
        },
    )
    second = await client.post(
        "/api/knowledge-material/uploads", content=data, headers={"X-Filename": "scan.pdf"}
    )
    assert second.status_code == 200
    assert second.json()["sha256"] == source["sha256"]
    assert second.json()["document_id"] == source["document_id"]
    versions = list(
        (
            await db.scalars(
                select(DocumentVersion)
                .where(DocumentVersion.document_id == source["document_id"])
                .order_by(DocumentVersion.version)
            )
        ).all()
    )
    assert len(versions) == 2 and versions[0].content_hash == original_hash
    assert versions[1].content_hash != original_hash
    previous_text = " ".join(
        (
            await db.scalars(select(Chunk.text).where(Chunk.document_version_id == versions[0].id))
        ).all()
    )
    assert "Table privileges" in previous_text
    assert len(list((tmp_path / "private").rglob("*.extraction-*.json"))) == 2


@runtime
async def test_empty_ocr_page_is_reported_in_mixed_upload(client, settings, tmp_path, monkeypatch):
    settings.knowledge_authoring_root = str(tmp_path / "private")
    data = scanned_pdf(tmp_path, mixed=True)
    monkeypatch.setattr(
        "app.knowledge.ingest.pdf.ocr_pages", lambda data, pages, opts: {p: "" for p in pages}
    )
    response = await client.post(
        "/api/knowledge-material/uploads", content=data, headers={"X-Filename": "mixed.pdf"}
    )
    assert response.status_code == 200, response.text
    assert response.json()["ocr_empty_pages"] == [2]
    assert "Table privileges" in response.json()["text"]


def test_legacy_native_pdf_loader_does_not_require_ocr_for_a_short_page(monkeypatch):
    from pypdf import PdfWriter
    from pypdf.generic import DecodedStreamObject, NameObject

    import app.knowledge.ingest.pdf as loader

    writer = PdfWriter()
    writer.add_page(PdfReader(io.BytesIO(native_pdf())).pages[0])
    content = DecodedStreamObject()
    content.set_data(b"BT /F1 14 Tf 40 720 Td (Keep this native heading) Tj ET")
    writer.pages[0][NameObject("/Contents")] = writer._add_object(content)
    buffer = io.BytesIO()
    writer.write(buffer)
    monkeypatch.setattr(loader, "_has_image", lambda resources: True)
    assert loader.pdf_blocks(buffer.getvalue())[0].text == "Keep this native heading"
    with pytest.raises(PdfOcrUnavailable):
        loader.pdf_blocks(buffer.getvalue(), require_complete=True)
