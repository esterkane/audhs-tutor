"""Fixed external-reference catalog and exact local copies; no question-derived network input."""

import hashlib
import json
import os
import tempfile
from dataclasses import dataclass
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.db.base import utcnow_iso
from app.knowledge import reference_fetch
from app.knowledge.ingest.htmltext import html_blocks
from app.knowledge.ingest.service import ingest_source
from app.knowledge.ingest.types import SourceDoc
from app.knowledge.repository import RetrievalRepository
from app.schemas.references import ReferenceImported, ReferenceSnapshot


@dataclass(frozen=True)
class Reference:
    id: str
    url: str
    title: str
    license_url: str


CATALOG = {
    item.id: item
    for item in (
        Reference(
            "python-tutorial",
            "https://docs.python.org/3/tutorial/",
            "Python tutorial",
            "https://docs.python.org/3/license.html",
        ),
        Reference(
            "numpy-basics",
            "https://numpy.org/doc/stable/user/absolute_beginners.html",
            "NumPy array basics",
            "https://numpy.org/doc/stable/license.html",
        ),
        Reference(
            "sklearn-preprocessing",
            "https://scikit-learn.org/stable/modules/preprocessing.html",
            "Data preprocessing with scikit-learn",
            "https://scikit-learn.org/stable/about.html",
        ),
        Reference(
            "python-data-structures",
            "https://docs.python.org/3/tutorial/datastructures.html",
            "Python lists, tuples and dictionaries",
            "https://docs.python.org/3/license.html",
        ),
        Reference(
            "pandas-tables",
            "https://pandas.pydata.org/docs/getting_started/intro_tutorials/01_table_oriented.html",
            "Tabular data with pandas",
            "https://pandas.pydata.org/docs/getting_started/overview.html",
        ),
        Reference(
            "sklearn-evaluation",
            "https://scikit-learn.org/stable/modules/model_evaluation.html",
            "Model evaluation metrics with scikit-learn",
            "https://scikit-learn.org/stable/about.html",
        ),
    )
}


def card(identity: str) -> Reference:
    if identity not in CATALOG:
        raise AppError("reference_not_found", "This curated reference is unavailable.", 404)
    return CATALOG[identity]


def _atomic(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        mode="w", encoding="utf-8", dir=path.parent, delete=False
    ) as temp:
        try:
            temp.write(content)
            temp.flush()
            os.fsync(temp.fileno())
            os.replace(temp.name, path)
        finally:
            Path(temp.name).unlink(missing_ok=True)


def _read(root: Path, reference: Reference, identity: str) -> tuple[ReferenceSnapshot, SourceDoc]:
    if len(identity) != 64 or any(c not in "0123456789abcdef" for c in identity):
        raise AppError(
            "reference_copy_invalid",
            "Local reference copy is unreadable. Explicitly refresh it to recover.",
            409,
        )
    path = root / reference.id / f"{identity}.json"
    try:
        if path.stat().st_size > reference_fetch.MAX_BYTES * 6 + 4000:
            raise ValueError("Oversized cache record")
        raw = json.loads(path.read_text(encoding="utf-8"))
        page = raw["html"]
        if not isinstance(page, str) or hashlib.sha256(page.encode()).hexdigest() != identity:
            raise ValueError("Snapshot hash mismatch")
        if raw["url"] != reference.url or raw["extraction_version"] != "html-blocks.v1":
            raise ValueError("Snapshot origin mismatch")
        title, blocks = html_blocks(page)
        text = "\n\n".join(block.text for block in blocks)
        if not text.strip():
            raise ValueError("No readable text")
        view = ReferenceSnapshot(
            reference_id=reference.id,
            snapshot_id=identity,
            url=reference.url,
            title=title or reference.title,
            fetched_at=raw["fetched_at"],
            license_url=reference.license_url,
            text_preview=text[:6000],
            extracted_characters=len(text),
        )
        doc = SourceDoc(
            title=title or reference.title,
            uri=reference.url,
            source_type="html",
            blocks=blocks,
            content_hash=identity,
            meta={"reference_snapshot": identity, "fetched_at": raw["fetched_at"]},
        )
        return view, doc
    except (OSError, ValueError, KeyError, TypeError) as exc:
        raise AppError(
            "reference_copy_invalid",
            "Local reference copy is unavailable or changed. Refresh explicitly before using it.",
            409,
        ) from exc


def current(root: Path, identity: str) -> ReferenceSnapshot | None:
    reference = card(identity)
    pointer = root / reference.id / "latest"
    if not pointer.exists():
        return None
    if pointer.stat().st_size > 64:
        raise AppError(
            "reference_copy_invalid",
            "Local reference pointer is unreadable. Refresh explicitly.",
            409,
        )
    return _read(root, reference, pointer.read_text())[0]


async def load(root: Path, identity: str, *, refresh: bool = False) -> ReferenceSnapshot:
    reference = card(identity)
    if not refresh:
        existing = current(root, identity)
        if existing:
            return existing
    fetched = await reference_fetch.fetch(reference.url)
    try:
        page = fetched.raw.decode("utf-8")
    except UnicodeError as exc:
        raise AppError(
            "reference_encoding", "This page is not UTF-8; no reading copy saved.", 422
        ) from exc
    _, blocks = html_blocks(page)
    if not blocks or not any(block.text.strip() for block in blocks):
        raise AppError("reference_empty", "No readable text found. No reading copy saved.", 422)
    snapshot_id = hashlib.sha256(fetched.raw).hexdigest()
    path = root / reference.id / f"{snapshot_id}.json"
    # A content hash identifies the retained original, not a moving latest-page assertion.
    _atomic(
        path,
        json.dumps(
            {
                "url": reference.url,
                "fetched_at": utcnow_iso(),
                "extraction_version": "html-blocks.v1",
                "html": page,
            },
            ensure_ascii=False,
        ),
    )
    _atomic(root / reference.id / "latest", snapshot_id)
    return _read(root, reference, snapshot_id)[0]


async def import_copy(
    db: AsyncSession, repo: RetrievalRepository, root: Path, identity: str, snapshot_id: str
) -> ReferenceImported:
    _, doc = _read(root, card(identity), snapshot_id)
    try:
        result = await ingest_source(db, doc, trust_tier=1, repo=repo)
    except Exception as exc:
        await db.rollback()
        raise AppError(
            "reference_import_failed",
            "The reading copy is kept, but library import failed. Check local retrieval/model readiness, then retry.",
            503,
        ) from exc
    return ReferenceImported(
        document_id=result.document_id,
        chunks=result.chunks,
        indexed=result.indexed,
        changed=result.changed,
    )
