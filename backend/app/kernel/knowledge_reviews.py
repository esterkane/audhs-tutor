"""Factual-review scheduling and revision proposals; never edits accepted versions."""

import copy
from datetime import UTC, datetime, timedelta
from typing import Any
from urllib.parse import urlsplit, urlunsplit
from uuid import uuid4

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.db.base import utcnow_iso
from app.db.models import CurriculumDraft, KnowledgeReview
from app.kernel import curriculum
from app.schemas.knowledge_reviews import FactualReviewOut, ReviewPolicyIn


def later(days: int) -> str:
    return (datetime.now(UTC) + timedelta(days=days)).isoformat(timespec="milliseconds")


def out(row: KnowledgeReview) -> FactualReviewOut:
    return FactualReviewOut(
        id=row.id,
        draft_id=row.draft_id,
        enabled=row.enabled,
        interval_days=row.interval_days,
        urls=row.urls_json,
        next_due_at=row.next_due_at,
        history=row.history_json,
    )


async def get(db: AsyncSession, learner_id: str, draft_id: str) -> KnowledgeReview | None:
    await curriculum.get_draft(db, learner_id, draft_id)
    result: KnowledgeReview | None = await db.scalar(
        select(KnowledgeReview).where(
            KnowledgeReview.learner_id == learner_id, KnowledgeReview.draft_id == draft_id
        )
    )

    return result


async def configure(
    db: AsyncSession, learner_id: str, draft_id: str, body: ReviewPolicyIn
) -> KnowledgeReview:
    draft = await curriculum.get_draft(db, learner_id, draft_id)
    if draft.status != "published" or not draft.payload_json.get("authoring"):
        raise AppError(
            "review_requires_accepted",
            "Activate your knowledge material before scheduling factual reviews.",
            409,
        )
    urls = []
    for url in body.urls:
        try:
            parsed = urlsplit(url.strip())
            if (
                parsed.scheme != "https"
                or not parsed.hostname
                or parsed.username
                or parsed.password
                or parsed.query
                or parsed.port not in (None, 443)
                or len(url) > 2000
            ):
                raise ValueError
        except ValueError as exc:
            raise AppError(
                "review_url_invalid",
                "Use public HTTPS documentation URLs without credentials or queries.",
                422,
            ) from exc
        urls.append(urlunsplit((parsed.scheme, parsed.netloc, parsed.path, "", "")))
    row = await get(db, learner_id, draft_id)
    if row is None:
        row = KnowledgeReview(learner_id=learner_id, draft_id=draft_id)
        db.add(row)
    if row.running_until and row.running_until > utcnow_iso():
        raise AppError("review_busy", "A factual review is already running.", 409)
    row.enabled = body.enabled
    row.interval_days = body.interval_days
    row.urls_json = list(dict.fromkeys(urls))
    row.next_due_at = utcnow_iso()
    await db.commit()
    await db.refresh(row)
    return row


async def propose_revision(
    db: AsyncSession, learner_id: str, draft_id: str, run_id: str
) -> CurriculumDraft:
    await db.commit()
    await db.execute(text("BEGIN IMMEDIATE"))
    row = await get(db, learner_id, draft_id)
    run = next((r for r in (row.history_json if row else []) if r.get("id") == run_id), None)
    if not run or not run.get("proposal", {}).get("proposed_explanation"):
        raise AppError("review_proposal_missing", "This review has no proposed explanation.", 409)
    assert row is not None
    if run.get("revision_id"):
        return await curriculum.get_draft(db, learner_id, run["revision_id"])
    original = await curriculum.get_draft(db, learner_id, draft_id)
    if original.status != "published" or original.version != run["draft_version"]:
        raise AppError(
            "review_version_changed",
            "Review the current accepted version before creating a revision.",
            409,
        )
    payload: dict[str, Any] = copy.deepcopy(original.payload_json)
    authoring = payload["authoring"]
    explanation = run["proposal"]["proposed_explanation"]
    authoring.update(
        explanation=explanation,
        revised_from_draft_id=draft_id,
        factual_review_id=run_id,
        request_id=str(uuid4()),
    )
    if payload.get("learning_objects"):
        payload["learning_objects"][0]["examples"][0] = explanation
    revision = CurriculumDraft(
        learner_id=learner_id,
        course=None,
        section=None,
        payload_json=payload,
        origin="knowledge_authored",
        status="draft",
        title=original.title,
        validation_json=curriculum.problems_json(await curriculum.validate_payload(db, payload)),
        version=1,
    )
    db.add(revision)
    await db.flush()
    db.add(
        KnowledgeReview(
            learner_id=learner_id,
            draft_id=revision.id,
            enabled=row.enabled,
            interval_days=row.interval_days,
            urls_json=list(row.urls_json),
            next_due_at=row.next_due_at,
        )
    )
    row.history_json = [
        {**item, "revision_id": revision.id} if item["id"] == run_id else item
        for item in row.history_json
    ]
    await db.commit()
    return revision
