"""Read-only owned review presentation. Binding validity is not source correctness."""

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import answer_checks
from app.db.models import Chunk, Document, DocumentVersion
from app.orchestrator.answer_check_binding import load_bound_review, text_hash
from app.orchestrator.ask import owned_answer
from app.schemas.answer_checks import AnswerCheckDetail, CheckedPassageStatus, SavedAnswerReview


async def detail(db: AsyncSession, learner_id: str, check_id: str) -> AnswerCheckDetail:
    row = await answer_checks.owned(db, learner_id, check_id)
    answer = await owned_answer(db, learner_id, row.answer_id)
    await db.refresh(answer)
    result = AnswerCheckDetail(
        id=row.id,
        answer_id=row.answer_id,
        created_at=row.created_at,
        binding_status="invalid_record",
    )
    try:
        receipt = SavedAnswerReview.model_validate_json(row.receipt_json)
    except ValueError:
        result.note = "This saved check cannot be read safely. The original answer is retained."
        return result
    newest = (
        select(DocumentVersion.document_id, func.max(DocumentVersion.version).label("version"))
        .group_by(DocumentVersion.document_id)
        .subquery()
    )
    rows = await db.execute(
        select(
            Chunk.id,
            Chunk.text,
            Document.title,
            DocumentVersion.version,
            newest.c.version.label("newest"),
        )
        .join(DocumentVersion, Chunk.document_version_id == DocumentVersion.id)
        .join(Document, Document.id == DocumentVersion.document_id)
        .join(newest, newest.c.document_id == Document.id)
        .where(Chunk.id.in_(receipt.passage_hashes))
    )
    current = {item.id: item for item in rows}
    for identity, digest in receipt.passage_hashes.items():
        item = current.get(identity)
        result.passages.append(
            CheckedPassageStatus(
                passage_id=identity,
                title=item.title if item else None,
                document_version=item.version if item else None,
                newer_version_available=bool(item and item.newest > item.version),
                binding_status=(
                    "missing"
                    if item is None
                    else "unchanged"
                    if text_hash(item.text) == digest
                    else "changed"
                ),
            )
        )
    try:
        load_bound_review(row.receipt_json, answer.text, {k: v.text for k, v in current.items()})
    except ValueError:
        result.binding_status = "changed_or_missing"
        result.note = "Answer or source text changed or is unavailable. This review is historical."
    else:
        result.binding_status = "unchanged"
    # Historical proposal is explicitly labelled and never promoted to current truth.
    result.proposal = receipt.proposal
    return result
