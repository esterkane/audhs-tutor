"""PDF text extraction with optional bounded OCR for pages containing scanned images."""

import re
import time
from dataclasses import replace
from typing import Any

from app.knowledge.ingest.pdf_ocr import PdfOcrOptions, PdfOcrUnavailable, ocr_pages, visible_pages
from app.knowledge.ingest.types import Block


class PdfSupportMissing(RuntimeError):
    pass


def _clean_page(text: str) -> str:
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"(?<=[a-z,;])\n(?=[a-z])", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _has_image(resources: Any, depth: int = 0) -> bool:
    if depth > 4 or not resources:
        return False
    resources = resources.get_object() if hasattr(resources, "get_object") else resources
    objects = resources.get("/XObject", {})
    objects = objects.get_object() if hasattr(objects, "get_object") else objects
    for ref in objects.values():
        obj = ref.get_object()
        if obj.get("/Subtype") == "/Image":
            return True
        if obj.get("/Subtype") == "/Form" and _has_image(obj.get("/Resources"), depth + 1):
            return True
    return False


def pdf_blocks(
    data: bytes,
    *,
    kind: str = "prose",
    ocr: PdfOcrOptions | None = None,
    extraction: dict[str, Any] | None = None,
    require_complete: bool = False,
) -> list[Block]:
    try:
        from io import BytesIO

        from pypdf import PdfReader
    except ImportError as e:
        raise PdfSupportMissing(
            "PDF ingest needs the optional `pypdf` package: uv add pypdf"
        ) from e
    reader = PdfReader(BytesIO(data))
    native: dict[int, str] = {}
    scanned: list[int] = []
    artwork: list[int] = []
    for i, page in enumerate(reader.pages, 1):
        native[i] = _clean_page(page.extract_text() or "")
        if len(native[i]) >= 80:
            continue
        if _has_image(page.get("/Resources")):
            scanned.append(i)
            continue
        # An inline image is a painting operation and needs no resource entry.
        content = page.get_contents()
        if content is not None and any(op == b"INLINE IMAGE" for _, op in content.operations):
            scanned.append(i)
        elif (
            require_complete
            and not native[i]
            and content is not None
            and any(
                op in {b"S", b"s", b"f", b"F", b"f*", b"B", b"B*", b"b", b"b*", b"Do", b"sh"}
                for _, op in content.operations
            )
        ):
            artwork.append(i)
    started = time.monotonic()
    recognized: dict[int, str] = {}
    if scanned and ocr is None and require_complete:
        raise PdfOcrUnavailable(
            "This PDF has scanned pages. Enable local OCR and install Poppler and Tesseract on the backend."
        )
    if scanned and ocr is not None:
        recognized = ocr_pages(data, scanned, ocr)
        if extraction is not None:
            extraction.update(
                engine="tesseract",
                languages=ocr.languages,
                ocr_pages=scanned,
                empty_ocr_pages=[p for p, value in recognized.items() if not value.strip()],
                latency_ms=round((time.monotonic() - started) * 1000),
            )
    if require_complete and extraction is not None:
        candidates = artwork + [
            i for i, text in recognized.items() if not text.strip() and not native[i]
        ]
        if candidates:
            options = ocr or PdfOcrOptions()
            remaining = options.timeout_s - (time.monotonic() - started)
            extraction["visual_pages"] = visible_pages(
                data, sorted(candidates), replace(options, timeout_s=remaining)
            )
    blocks: list[Block] = []
    for i, native_text in native.items():
        text = _clean_page(recognized[i]) if i in recognized else native_text
        # Preserve short selectable headers too, even if OCR misses or changes them.
        if native_text and native_text not in text:
            text = native_text + ("\n\n" + text if text else "")
        if not text:
            continue
        blocks.append(
            Block(text=text, kind="slide" if kind == "slide" else "prose", heading=f"p. {i}")
        )
    return blocks
