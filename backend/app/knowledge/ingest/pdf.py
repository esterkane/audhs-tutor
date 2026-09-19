"""PDF (slides exports, papers) -> one block per page. Text extraction uses `pypdf`, imported
lazily: it is an optional extra that the owner installs deliberately (`uv add pypdf`). Without it
the loader raises `PdfSupportMissing` and the ingest run reports the file as skipped."""

import re

from app.knowledge.ingest.types import Block


class PdfSupportMissing(RuntimeError):
    pass


def _clean_page(text: str) -> str:
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"(?<=[a-z,;])\n(?=[a-z])", " ", text)  # re-join wrapped lines
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def pdf_blocks(data: bytes, *, kind: str = "prose") -> list[Block]:
    try:
        from io import BytesIO

        from pypdf import PdfReader
    except ImportError as e:  # pragma: no cover - exercised only without the extra
        raise PdfSupportMissing(
            "PDF ingest needs the optional `pypdf` package: uv add pypdf"
        ) from e
    reader = PdfReader(BytesIO(data))
    blocks: list[Block] = []
    for i, page in enumerate(reader.pages, 1):
        text = _clean_page(page.extract_text() or "")
        if len(text) < 20:
            continue  # blank or image-only page
        blocks.append(
            Block(text=text, kind="slide" if kind == "slide" else "prose", heading=f"p. {i}")
        )
    return blocks
