"""Fetch fresh bounded evidence and propose a review; never rewrite accepted lessons."""

import hashlib
import json
import re
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.core.errors import AppError
from app.db.base import new_id, utcnow_iso
from app.db.models import CurriculumDraft, KnowledgeReview
from app.kernel import curriculum
from app.kernel import knowledge_reviews as policies
from app.knowledge import reference_fetch
from app.knowledge.ingest.htmltext import html_blocks
from app.models_ai.gateway import ModelGateway
from app.models_ai.provider import Message, TaskClass
from app.orchestrator import personas
from app.orchestrator.authoring_gateway import AuthoringGateway, choose
from app.orchestrator.context import escape_data
from app.orchestrator.prompts import _read
from app.schemas.knowledge_reviews import FactualProposal


async def snapshot(url: str, focus: str) -> dict[str, Any]:
    page = await reference_fetch.fetch(url)
    _, blocks = html_blocks(page.raw.decode("utf-8", errors="replace"))
    paragraphs = [b.text for b in blocks if b.text.strip()]
    terms = set(re.findall(r"\w{3,}", focus.casefold()))
    ranked = sorted(
        range(len(paragraphs)),
        key=lambda i: len(terms & set(re.findall(r"\w{3,}", paragraphs[i].casefold()))),
        reverse=True,
    )
    selected = sorted(ranked[:8])
    excerpt = "\n\n".join(paragraphs[i][:1500] for i in selected)[:6000]
    if not excerpt:
        raise AppError(
            "review_source_empty", "No readable evidence was found in this reference.", 422
        )
    digest = hashlib.sha256("\n\n".join(paragraphs).encode()).hexdigest()
    return {"url": url, "sha256": digest, "excerpt": excerpt, "fetched_at": utcnow_iso()}


async def run(
    db: AsyncSession,
    gateway: ModelGateway,
    settings: Settings,
    learner_id: str,
    draft_id: str,
    *,
    manual: bool = True,
) -> KnowledgeReview:
    row = await policies.get(db, learner_id, draft_id)
    if row is None or not row.enabled:
        raise AppError("review_not_enabled", "Enable a factual review schedule first.", 409)
    draft = await curriculum.get_draft(db, learner_id, draft_id)
    if draft.status != "published":
        raise AppError("review_requires_accepted", "This material has not been activated.", 409)
    slug = (draft.payload_json.get("skills") or [{}])[0].get("slug")
    latest = await db.scalar(
        select(CurriculumDraft)
        .where(
            CurriculumDraft.learner_id == learner_id,
            CurriculumDraft.status == "published",
            CurriculumDraft.payload_json["skills"][0]["slug"].as_string() == slug,
        )
        .order_by(CurriculumDraft.published_at.desc())
        .limit(1)
    )
    if latest and latest.id != draft.id:
        row.enabled = False
        await db.commit()
        return row
    selected = await choose(gateway, settings, learner_id, draft_id, draft.version)
    if not isinstance(selected, AuthoringGateway):
        raise AppError(
            "review_hosted_disabled", "Enable hosted authoring for factual reviews.", 409
        )
    now = utcnow_iso()
    conditions = [
        KnowledgeReview.id == row.id,
        or_(KnowledgeReview.running_until.is_(None), KnowledgeReview.running_until <= now),
    ]
    if not manual:
        conditions.append(KnowledgeReview.next_due_at <= now)
    claimed = await db.execute(
        update(KnowledgeReview)
        .where(*conditions)
        .values(
            running_until=(datetime.now(UTC) + timedelta(minutes=10)).isoformat(
                timespec="milliseconds"
            )
        )
    )
    if getattr(claimed, "rowcount", 0) != 1:
        raise AppError("review_busy", "A review is running or is not yet due.", 409)
    await db.commit()
    record: dict[str, Any] = {
        "id": new_id(),
        "draft_id": draft.id,
        "draft_version": draft.version,
        "checked_at": now,
    }
    try:
        material = draft.payload_json["authoring"]
        fields = {
            k: material.get(k, "")
            for k in ["title", "objective", "explanation", "worked_example", "question", "criteria"]
        }
        sources = [
            await snapshot(str(url), json.dumps(fields, ensure_ascii=False))
            for url in row.urls_json
        ]
        prior = next((r for r in reversed(row.history_json) if r.get("sources")), None)
        unchanged = bool(
            prior
            and [(s["url"], s["sha256"]) for s in prior["sources"]]
            == [(s["url"], s["sha256"]) for s in sources]
            and prior["draft_version"] == draft.version
            and prior.get("outcome") in ["reviewed", "sources_unchanged"]
        )
        record["sources"] = sources
        if unchanged:
            record["outcome"] = "sources_unchanged"
        else:
            presentation = await personas.load(db, learner_id)
            result = await selected.complete(
                TaskClass.EXPLAIN_SIMPLE,
                [
                    Message(
                        role="system",
                        content=_read("curriculum/factual-review.v1.md") + presentation.instruction,
                    ),
                    Message(
                        role="user",
                        content="<factual_review>\n"
                        + escape_data(
                            json.dumps(
                                {
                                    "lesson": fields,
                                    "sources": {
                                        str(i + 1): s["excerpt"] for i, s in enumerate(sources)
                                    },
                                },
                                ensure_ascii=False,
                            )
                        )
                        + "\n</factual_review>",
                    ),
                ],
                response_model=FactualProposal,
                learner_id=learner_id,
                max_tokens=2400,
                metadata={
                    "task": "factual_review",
                    "draft_id": draft.id,
                    "draft_version": draft.version,
                    "prompt_version": "curriculum.factual-review.v1",
                },
            )
            proposal = result.result.parsed
            if not isinstance(proposal, FactualProposal) or any(
                f.source_index > len(sources)
                or f.quote not in sources[f.source_index - 1]["excerpt"]
                for f in proposal.findings
            ):
                raise AppError(
                    "review_evidence_invalid",
                    "Review quotations did not match the fetched evidence.",
                    422,
                )
            record.update(
                outcome="reviewed",
                proposal=proposal.model_dump(),
                model_call_id=result.model_call_id,
            )
    except Exception as exc:
        record.update(
            outcome="failed",
            error=exc.code if isinstance(exc, AppError) else type(exc).__name__,
            error_message=exc.message
            if isinstance(exc, AppError)
            else "The review could not finish. Try again later.",
        )
    # The report is append-only history; a failure never becomes a successful check.
    await db.refresh(row)
    row.history_json = [*row.history_json, record]
    row.running_until = None
    row.next_due_at = policies.later(1 if record["outcome"] == "failed" else row.interval_days)
    await db.commit()
    await db.refresh(row)
    return row
