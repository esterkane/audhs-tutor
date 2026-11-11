"""Read a single raster image of a verified, learner-owned uploaded PDF page."""

import hashlib
import shutil
import subprocess
from pathlib import Path
from tempfile import TemporaryDirectory
from threading import BoundedSemaphore

from app.core.errors import AppError
from app.knowledge import pdf_page_sources
from app.knowledge.ingest.pdf_ocr import PdfOcrError, PdfOcrOptions, ocr_pages

_slots = BoundedSemaphore(2)


def verified_original(path: Path) -> bytes:
    with path.open("rb") as source:
        raw = source.read(10 * 1024 * 1024 + 1)
    if len(raw) > 10 * 1024 * 1024 or hashlib.sha256(raw).hexdigest() != path.stem:
        raise AppError("not_found", "The original PDF is unavailable.", 404)
    return raw


def render(path: Path, owner: Path, extraction_digest: str, page: int) -> bytes:
    pages = pdf_page_sources.read(path, owner, extraction_digest)
    if not any(item.page == page for item in pages.pages):
        raise AppError("not_found", "The saved PDF page is unavailable.", 404)
    if not _slots.acquire(blocking=False):
        raise AppError("preview_busy", "Another page is being prepared. Try again.", 429)
    try:
        raw = verified_original(path)
        executable = shutil.which("pdftoppm")
        if executable is None:
            raise AppError("preview_unavailable", "Poppler is required to preview this PDF.", 503)
        with TemporaryDirectory(prefix="audhs-pdf-preview-") as temp:
            prefix = Path(temp) / "page"
            subprocess.run(
                [
                    executable,
                    "-f",
                    str(page),
                    "-l",
                    str(page),
                    "-singlefile",
                    "-scale-to",
                    "1800",
                    "-png",
                    "-",
                    str(prefix),
                ],
                input=raw,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=12,
                check=True,
            )
            return prefix.with_suffix(".png").read_bytes()
    except FileNotFoundError as exc:
        raise AppError("not_found", "The original PDF page is unavailable.", 404) from exc
    except (subprocess.SubprocessError, OSError) as exc:
        raise AppError("preview_failed", "Could not render this PDF page.", 422) from exc
    finally:
        _slots.release()


def read_table_rows(path: Path, owner: Path, digest: str, page: int, options: PdfOcrOptions) -> str:
    manifest = pdf_page_sources.read(path, owner, digest)
    if not any(item.page == page and item.ocr for item in manifest.pages):
        raise AppError("not_found", "This scanned page is unavailable.", 404)
    if not _slots.acquire(blocking=False):
        raise AppError("preview_busy", "Another page is being prepared. Try again.", 429)
    try:
        return ocr_pages(verified_original(path), [page], options, table_rows=True)[page]
    except OSError as exc:
        raise AppError("not_found", "The original PDF is unavailable.", 404) from exc
    except PdfOcrError as exc:
        raise AppError(exc.code, str(exc), 422) from exc
    finally:
        _slots.release()
