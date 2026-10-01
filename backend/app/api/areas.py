"""Knowledge-area catalog, local draft jobs and explicit question feedback."""

import asyncio

from fastapi import APIRouter, Request
from pydantic import BaseModel

from app.api.deps import DB, Learner, SettingsDep
from app.core.errors import AppError
from app.kernel import areas, question_feedback
from app.orchestrator import area_drafting
from app.schemas.areas import (
    AreaEdit,
    AreaList,
    AreaSources,
    FeedbackIn,
    FeedbackList,
    FeedbackOut,
    FeedbackPreference,
)

router = APIRouter(prefix="/areas", tags=["areas"])


class AreaJobIn(BaseModel):
    area_id: str | None = None
    force_new: bool = False


class AreaJobOut(BaseModel):
    running: bool = False
    current: str | None = None
    finished: int = 0
    total: int = 0
    results: list[dict[str, str]] = []
    error: str | None = None


@router.get("", summary="Editable areas across all imported courses", response_model=AreaList)
async def catalogue(db: DB, learner: Learner) -> AreaList:
    return AreaList(**await areas.catalogue(db, learner.id))


@router.post(
    "/initialize",
    summary="Create missing suggested areas without changing existing labels",
    response_model=AreaList,
)
async def initialize(db: DB, learner: Learner) -> AreaList:
    await areas.seed(db)
    return await catalogue(db, learner)


@router.put(
    "/{area_id}",
    summary="Edit an area label and its source matching terms",
    response_model=AreaList,
)
async def edit(area_id: str, body: AreaEdit, db: DB, learner: Learner) -> AreaList:
    row = await areas.get(db, area_id)
    terms = [s.strip()[:100] for s in body.terms if s.strip()]
    if len(body.title.strip()) < 2:
        raise ValueError("area title must contain at least two characters")
    if not terms:
        raise ValueError("at least one nonempty matching term is required")
    row.title, row.description, row.terms_json = (
        body.title.strip(),
        body.description,
        list(dict.fromkeys(terms)),
    )
    await db.commit()
    return await catalogue(db, learner)


@router.get(
    "/{area_id}/sources",
    summary="Cross-course source candidates and why they match",
    response_model=AreaSources,
)
async def sources(area_id: str, db: DB) -> AreaSources:
    return AreaSources(sources=await areas.source_rows(db, await areas.get(db, area_id)))


@router.get(
    "/draft-job/status", summary="Progress of the local area draft batch", response_model=AreaJobOut
)
async def job_status(request: Request) -> AreaJobOut:
    return getattr(request.app.state, "area_job_status", AreaJobOut())


@router.post(
    "/draft-job/start",
    summary="Create missing area drafts sequentially with local models only",
    response_model=AreaJobOut,
)
async def start(
    request: Request,
    db: DB,
    learner: Learner,
    settings: SettingsDep,
    body: AreaJobIn | None = None,
) -> AreaJobOut:
    state = getattr(request.app.state, "area_job_status", None)
    if state is not None and state.running:
        raise AppError("busy", "Area drafts are already being generated", http_status=409)
    options = body or AreaJobIn()
    if options.force_new and not options.area_id:
        raise ValueError("Choose one area when requesting a new draft")
    state = AreaJobOut(running=True)
    request.app.state.area_job_status = state
    try:
        await areas.seed(db)
        if options.area_id:
            await areas.get(db, options.area_id)
            ids = [options.area_id]
        else:
            catalog = await areas.catalogue(db, learner.id)
            ids = [a["id"] for a in catalog["areas"] if a["documents"]]
        state.total = len(ids)
    except BaseException:
        state.running = False
        raise
    factory = request.app.state.session_factory
    owner_id = learner.id

    async def run() -> None:
        try:
            for area_id in ids:
                async with factory() as work:
                    area = await areas.get(work, area_id)
                    state.current = area.title
                    draft_id, result = await area_drafting.create_or_generate(
                        work, settings, owner_id, area_id, force_new=options.force_new
                    )
                    state.results.append(
                        {"area": area.title, "draft_id": draft_id, "result": result}
                    )
                    state.finished += 1
        except asyncio.CancelledError:
            state.error = (
                "Stopped; completed drafts are kept. Start again to continue missing areas."
            )
        except Exception as e:
            state.error = type(e).__name__ + ": batch stopped; completed drafts are kept."
        finally:
            state.running, state.current = False, None

    request.app.state.area_job_task = asyncio.create_task(run())
    return state


@router.post(
    "/draft-job/stop",
    summary="Stop generation and keep completed drafts",
    response_model=AreaJobOut,
)
async def stop(request: Request) -> AreaJobOut:
    task = getattr(request.app.state, "area_job_task", None)
    if task and not task.done():
        task.cancel()
        await task
    return await job_status(request)


@router.post(
    "/feedback/questions",
    summary="Rate a versioned question with labels and a reason",
    response_model=FeedbackOut,
)
async def feedback(body: FeedbackIn, db: DB, learner: Learner) -> FeedbackOut:
    return FeedbackOut(
        **question_feedback.out(await question_feedback.record(db, learner.id, body))
    )


@router.get(
    "/feedback/questions",
    summary="Question feedback and explicit generation preferences",
    response_model=FeedbackList,
)
async def feedback_list(db: DB, learner: Learner) -> FeedbackList:
    return FeedbackList(**await question_feedback.summary(db, learner.id))


@router.delete(
    "/feedback/questions/{feedback_id}",
    summary="Withdraw feedback without rewriting learning history",
    response_model=FeedbackList,
)
async def withdraw(feedback_id: str, db: DB, learner: Learner) -> FeedbackList:
    await question_feedback.withdraw(db, learner.id, feedback_id)
    return await feedback_list(db, learner)


@router.put(
    "/feedback/preferences",
    summary="Explicitly apply or undo a question preference",
    response_model=FeedbackList,
)
async def feedback_preference(body: FeedbackPreference, db: DB, learner: Learner) -> FeedbackList:
    await question_feedback.set_guidance(db, learner.id, body.key, body.enabled)
    return await feedback_list(db, learner)
