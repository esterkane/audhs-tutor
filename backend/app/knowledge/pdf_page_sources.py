"""Version-bound page text for learner-uploaded PDFs, kept beside the private original."""

import hashlib
import json
import os
import re
import tempfile
from pathlib import Path
from typing import Any

from app.knowledge.ingest.types import SourceDoc
from app.schemas.knowledge_authoring import PdfPageSource, PdfPageSources


def persist(path: Path, digest: str, doc: SourceDoc, languages: str) -> str:
    report = doc.meta.get("pdf_extraction", {})
    ocr = set(report.get("ocr_pages", []))
    pages: list[dict[str, Any]] = []
    for block in doc.blocks:
        match = re.fullmatch(r"p\. ([1-9]\d*)", block.heading or "")
        if match is None:
            raise ValueError("PDF extraction lost a physical page label")
        page = int(match[1])
        pages.append({"page": page, "text": block.text, "ocr": page in ocr})
    # A scan with no recognized text still has a physical page the learner can inspect.
    represented = {p["page"] for p in pages}
    for number in sorted(ocr - represented):
        pages.append({"page": number, "text": "", "ocr": True})
    pages.sort(key=lambda item: item["page"])
    evidence = {"sha256": digest, "pages": pages, "languages": languages, "format": 2}
    identity = _identity(evidence)
    dest = path.with_suffix(".pdf.extraction-" + identity + ".json")
    record = {**report, "evidence": evidence, "sha256": digest, "extraction_sha256": identity}
    with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as tmp:
        staging = Path(tmp.name)
    try:
        staging.write_text(json.dumps(record, ensure_ascii=False), encoding="utf-8")
        os.replace(staging, dest)
    finally:
        staging.unlink(missing_ok=True)
    return identity


def _identity(evidence: dict[str, Any]) -> str:
    return hashlib.sha256(
        json.dumps(evidence, ensure_ascii=False, sort_keys=True).encode()
    ).hexdigest()


def read(path: Path, owner_folder: Path, digest: str) -> PdfPageSources:
    if (
        not path.is_relative_to(owner_folder)
        or path.resolve() != path
        or not re.fullmatch(r"[a-f0-9]{64}\.pdf", path.name)
        or not re.fullmatch(r"[a-f0-9]{64}", digest)
    ):
        return PdfPageSources()
    audit = path.with_suffix(".pdf.extraction-" + digest + ".json")
    if audit.is_symlink() or not audit.is_file():
        return PdfPageSources()
    try:
        data = json.loads(audit.read_text(encoding="utf-8"))
        evidence = data["evidence"]
        if evidence["sha256"] != path.stem or _identity(evidence) != digest:
            return PdfPageSources()
        return PdfPageSources(pages=[PdfPageSource.model_validate(p) for p in evidence["pages"]])
    except (KeyError, TypeError, OSError, ValueError):
        return PdfPageSources()
