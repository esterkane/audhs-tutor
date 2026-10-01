"""P7 guided listening: lessons, bounded clips, media under the ingest roots, one task per clip.
Answers go through the ordinary `/api/assess/attempt` (grader → evidence → FSRS)."""

from typing import Any

from fastapi import APIRouter
from fastapi.responses import FileResponse

from app.api.deps import DB, Gateway, Learner, SettingsDep
from app.core.errors import AppError
from app.db.events import EventWriter, Verb
from app.kernel import listening
from app.kernel import session as ksession
from app.orchestrator import listening as gen
from app.orchestrator.grader import view
from app.schemas.common import ActivityType, Domain, ObjectType
from app.schemas.listening import (
    LessonList,
    LessonOut,
    LessonSummary,
    ListenedIn,
    SectionOut,
    SkippedOut,
    TaskIn,
    TaskOut,
    ValidateIn,
)

router = APIRouter(prefix="/listening", tags=["listening"])


async def _own_session(db: DB, learner_id: str, session_id: str) -> Any:
    session = await ksession.get(db, session_id)
    if session.learner_id != learner_id:
        raise AppError("not_found", "no such session", http_status=404)
    return session


def _media_url(document_id: str) -> str:
    return f"/api/listening/lessons/{document_id}/media"


@router.get(
    "/lessons",
    summary="Ingested timed documents usable as listening lessons (audio availability, progress)",
    response_model=LessonList,
)
async def list_lessons(db: DB, learner: Learner, settings: SettingsDep) -> LessonList:
    rows = await listening.lessons(db, learner.id, settings.ingest_roots_resolved)
    return LessonList(lessons=[LessonSummary(**r) for r in rows])


@router.get(
    "/lessons/{document_id}",
    summary="One lesson: bounded clips with transcript, progress, guarded media url",
    response_model=LessonOut,
)
async def get_lesson(
    document_id: str, db: DB, learner: Learner, settings: SettingsDep
) -> LessonOut:
    lesson = await listening.load_lesson(
        db, learner.id, document_id, settings.ingest_roots_resolved
    )
    if lesson is None:
        raise AppError("not_found", "no such document", http_status=404)
    note = None
    if lesson.media_path is None:
        note = "no audio file next to this transcript under the ingest roots — reading version"
    else:
        try:
            if lesson.media_path.stat().st_size > listening.MAX_MEDIA_BYTES:
                note = "audio file too large to serve — reading version"
        except OSError:
            note = "the audio file disappeared — reading version"
    return LessonOut(
        document_id=lesson.document_id,
        title=lesson.title,
        course=lesson.course,
        lecture=lesson.lecture,
        language=lesson.language,
        media_url=_media_url(lesson.document_id) if note is None else None,
        media_note=note,
        duration_s=lesson.duration_s,
        sections=[SectionOut(**s.__dict__) for s in lesson.sections],
        skipped=[SkippedOut(**k) for k in lesson.skipped],
        next_index=lesson.next_index,
    )


@router.get(
    "/lessons/{document_id}/media",
    summary="The lesson's audio/video (plain file under INGEST_ROOTS only; Range-capable)",
    response_class=FileResponse,
)
async def media(document_id: str, db: DB, learner: Learner, settings: SettingsDep) -> FileResponse:
    lesson = await listening.load_lesson(
        db, learner.id, document_id, settings.ingest_roots_resolved
    )
    if lesson is None or lesson.media_path is None:
        raise AppError("not_found", "no audio for this lesson under the ingest roots", 404)
    try:
        size = lesson.media_path.stat().st_size
    except OSError as e:
        raise AppError("not_found", "the audio file is gone", 404) from e
    if size > listening.MAX_MEDIA_BYTES:
        raise AppError("too_large", "audio file exceeds the serving limit", http_status=413)
    return FileResponse(lesson.media_path, filename=lesson.media_path.name)


@router.post(
    "/lessons/{document_id}/sections/{index}/task",
    summary="The comprehension task for one clip (created once; model-proposed or source-cut cloze)",
    response_model=TaskOut,
)
async def task(
    document_id: str,
    index: int,
    body: TaskIn,
    db: DB,
    learner: Learner,
    settings: SettingsDep,
    gateway: Gateway,
) -> TaskOut:
    session = await _own_session(db, learner.id, body.session_id)
    lesson = await listening.load_lesson(
        db, learner.id, document_id, settings.ingest_roots_resolved
    )
    if lesson is None:
        raise AppError("not_found", "no such document", http_status=404)
    if not 0 <= index < len(lesson.sections):
        raise AppError("bad_request", "no such clip", http_status=400)
    section = lesson.sections[index]
    # low capacity: never wait on a model; the source-cut cloze is immediate
    use_model = body.use_model and session.mode != "low_capacity"
    a, problems = await gen.ensure_task(
        db,
        gateway,
        lesson=lesson,
        section=section,
        learner_id=learner.id,
        session_id=session.id,
        use_model=use_model,
    )
    meta = (a.item_json or {}).get("listening") or {}
    return TaskOut(
        item=view(a),
        origin=str(meta.get("origin") or "deterministic"),
        validated=bool(meta.get("validated")),
        problems=problems,
        citation=await listening.provenance_citation(db, section.chunk_id, section.t_start),
        clip={"t_start": section.t_start, "t_end": section.t_end, "chunk_id": section.chunk_id},
    )


@router.post(
    "/tasks/{assessment_id}/validate",
    summary="Mark a model-proposed question as checked by you (full weight) or not",
    response_model=TaskOut,
)
async def validate(assessment_id: str, body: ValidateIn, db: DB, learner: Learner) -> TaskOut:
    a = await listening.validate_task(db, assessment_id, validated=body.validated)
    meta = (a.item_json or {}).get("listening") or {}
    return TaskOut(
        item=view(a),
        origin=str(meta.get("origin") or "deterministic"),
        validated=bool(meta.get("validated")),
        problems=[],
        citation=await listening.provenance_citation(
            db, str(meta.get("chunk_id")), meta.get("t_start")
        ),
        clip={
            "t_start": meta.get("t_start"),
            "t_end": meta.get("t_end"),
            "chunk_id": meta.get("chunk_id"),
        },
    )


@router.post(
    "/lessons/{document_id}/sections/{index}/listened",
    summary="Log that a clip was played (exposure, never evidence)",
    status_code=204,
)
async def listened(
    document_id: str, index: int, body: ListenedIn, db: DB, learner: Learner, settings: SettingsDep
) -> None:
    session = await _own_session(db, learner.id, body.session_id)
    if session.learner_id != learner.id:
        raise AppError("not_found", "no such session", http_status=404)
    lesson = await listening.load_lesson(
        db, learner.id, document_id, settings.ingest_roots_resolved
    )
    if lesson is None:
        raise AppError("not_found", "no such document", http_status=404)
    if not 0 <= index < len(lesson.sections):
        raise AppError("bad_request", "no such clip", http_status=400)
    events = EventWriter(
        db,
        ksession.event_context(
            session, domain=Domain.LANGUAGE, activity=ActivityType.DOMAIN_SWITCH
        ),
    )
    await events.emit(
        Verb.LISTENED,
        ObjectType.ITEM,
        body.chunk_id or f"{document_id}:{index}",
        result={"replays": body.replays, "seconds": body.seconds},
        context={"document_id": document_id, "clip_index": index},
    )
