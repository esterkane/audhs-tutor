"""Explicit authoring credentials and accepted-material review controls."""

import json

from fastapi import APIRouter, Request
from starlette.concurrency import run_in_threadpool

from app.api.curriculum import _draft_out
from app.api.deps import DB, Gateway, Learner, SettingsDep
from app.core.errors import AppError
from app.kernel import knowledge_reviews as policies
from app.kernel import preferences
from app.orchestrator import knowledge_reviews
from app.schemas.curriculum import DraftOut
from app.schemas.knowledge_reviews import AuthoringSetup, FactualReviewOut, ReviewPolicyIn

router = APIRouter(tags=["knowledge-material"])


@router.get("/authoring/setup", response_model=AuthoringSetup)
async def setup(
    db: DB, learner: Learner, settings: SettingsDep, gateway: Gateway
) -> AuthoringSetup:
    values = await preferences.get_all(db, learner.id)
    cap = int(values["authoring.daily_budget_cents"]) / 100
    spend = await gateway.budget.with_cap(cap).spend_today(db)
    key = await run_in_threadpool(settings.read_authoring_key)
    return AuthoringSetup(
        enabled=bool(values["authoring.enabled"]),
        key_configured=bool(key),
        model_id=str(values["authoring.model"]),
        daily_budget_usd=cap,
        counted_today_usd=spend.counted,
    )


@router.post("/authoring/key", response_model=AuthoringSetup)
async def save_key(
    request: Request, db: DB, learner: Learner, settings: SettingsDep, gateway: Gateway
) -> AuthoringSetup:
    # Parse manually: validation errors must never echo a submitted secret.
    from urllib.parse import urlsplit

    origin = request.headers.get("origin")
    if origin:
        parsed = urlsplit(origin)
        if parsed.hostname not in {"localhost", "127.0.0.1", "::1"}:
            raise AppError("key_origin_denied", "Open Authoring setup on this machine.", 403)
    raw = await request.body()
    if len(raw) > 4096:
        raise AppError("key_invalid", "Enter a valid OpenAI API key.", 422)
    try:
        body = json.loads(raw)
        key = body["key"]
        if (
            not isinstance(key, str)
            or not key.startswith("sk-")
            or not 20 <= len(key) <= 512
            or any(c.isspace() for c in key)
        ):
            raise ValueError
    except (ValueError, KeyError, TypeError) as exc:
        raise AppError("key_invalid", "Enter a valid OpenAI API key.", 422) from exc
    await run_in_threadpool(settings.save_authoring_key, key)
    return await setup(db, learner, settings, gateway)


@router.get(
    "/knowledge-material/drafts/{draft_id}/factual-review", response_model=FactualReviewOut | None
)
async def get_review(draft_id: str, db: DB, learner: Learner) -> FactualReviewOut | None:
    row = await policies.get(db, learner.id, draft_id)
    return policies.out(row) if row else None


@router.put("/knowledge-material/drafts/{draft_id}/factual-review", response_model=FactualReviewOut)
async def configure(
    draft_id: str, body: ReviewPolicyIn, db: DB, learner: Learner
) -> FactualReviewOut:
    return policies.out(await policies.configure(db, learner.id, draft_id, body))


@router.post(
    "/knowledge-material/drafts/{draft_id}/factual-review/run", response_model=FactualReviewOut
)
async def run(
    draft_id: str, db: DB, learner: Learner, gateway: Gateway, settings: SettingsDep
) -> FactualReviewOut:
    return policies.out(await knowledge_reviews.run(db, gateway, settings, learner.id, draft_id))


@router.post(
    "/knowledge-material/drafts/{draft_id}/factual-review/revisions/{run_id}",
    response_model=DraftOut,
)
async def revise(draft_id: str, run_id: str, db: DB, learner: Learner) -> DraftOut:
    return _draft_out(await policies.propose_revision(db, learner.id, draft_id, run_id))
