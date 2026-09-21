"""P4: material status, curriculum drafts (propose → edit → publish/reject), source passages for
citations, and content reports. Routers stay thin; the kernel decides."""

from fastapi import APIRouter
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlalchemy import select

from app.api.deps import DB, Gateway, Learner, SettingsDep
from app.core.errors import AppError
from app.db.models import ContentReport, CurriculumDraft
from app.kernel import curriculum
from app.orchestrator import drafting
from app.schemas.curriculum import (
    ArchiveRoleIn,
    ArchiveRoleOut,
    ChunkOut,
    CourseSourceList,
    CourseSourceOut,
    CourseSourceRoleIn,
    CourseSourceRoleOut,
    DraftCreate,
    DraftList,
    DraftOut,
    DraftUpdate,
    MaterialList,
    MaterialStatus,
    ProblemOut,
    PublishOut,
    ReportIn,
    ReportList,
    ReportOut,
    SectionList,
    SectionOut,
)

router = APIRouter(prefix="/curriculum", tags=["curriculum"])


def _draft_out(d: CurriculumDraft) -> DraftOut:
    return DraftOut(
        id=d.id,
        course=d.course,
        section=d.section,
        title=d.title,
        status=d.status,
        origin=d.origin,
        version=d.version,
        payload=dict(d.payload_json or {}),
        problems=[ProblemOut(**p) for p in (d.validation_json or [])],
        created_at=d.created_at,
        updated_at=d.updated_at,
        published_at=d.published_at,
        model_call_id=d.model_call_id,
    )


@router.get(
    "/material",
    summary="Per course: imported → searchable → draft → published",
    response_model=MaterialList,
)
async def material(db: DB, learner: Learner) -> MaterialList:
    rows = await curriculum.material_status(db, learner.id)
    return MaterialList(courses=[MaterialStatus(**m) for m in rows])


@router.get(
    "/sections", summary="Sections of a course with document counts", response_model=SectionList
)
async def sections(course: str, db: DB) -> SectionList:
    return SectionList(
        course=course, sections=[SectionOut(**s) for s in await curriculum.sections_of(db, course)]
    )


@router.get(
    "/sources",
    summary="Every document of a course with its role for drafting (owner decision or suggestion)",
    response_model=CourseSourceList,
)
async def sources(course: str, db: DB) -> CourseSourceList:
    rows = await curriculum.course_sources(db, course)
    counts = {r: 0 for r in curriculum.SOURCE_ROLES}
    for r in rows:
        counts[str(r["role"])] += 1
    return CourseSourceList(
        course=course,
        sources=[
            CourseSourceOut(**{k: v for k, v in r.items() if k not in ("section_no", "lecture_no")})
            for r in rows
        ],
        counts=counts,
    )


@router.put(
    "/sources/{document_id}",
    summary="Decide a document's role for its course (primary | supplemental | excluded)",
    response_model=CourseSourceRoleOut,
)
async def set_source(
    document_id: str, course: str, body: CourseSourceRoleIn, db: DB
) -> CourseSourceRoleOut:
    try:
        res = await curriculum.set_source_role(db, course, document_id, body.role, body.reason)
    except KeyError as e:
        raise AppError("not_found", f"document {document_id} is not in course {course}", 404) from e
    return CourseSourceRoleOut(document_id=document_id, **res)


@router.put(
    "/sources-archive",
    summary="Decide the role of every member of one bundled archive at once",
    response_model=ArchiveRoleOut,
)
async def set_archive(course: str, body: ArchiveRoleIn, db: DB) -> ArchiveRoleOut:
    n = await curriculum.set_archive_role(db, course, body.archive, body.role, body.reason)
    if n == 0:
        raise AppError("not_found", f"no members of archive {body.archive!r} in {course}", 404)
    return ArchiveRoleOut(archive=body.archive, role=body.role, documents=n)


@router.delete(
    "/sources/{document_id}",
    summary="Drop the owner's decision: the suggested role applies again",
    response_model=CourseSourceRoleOut,
)
async def reset_source(document_id: str, course: str, db: DB) -> CourseSourceRoleOut:
    try:
        res = await curriculum.reset_source_role(db, course, document_id)
    except KeyError as e:
        raise AppError("not_found", f"document {document_id} not found", 404) from e
    return CourseSourceRoleOut(document_id=document_id, **res)


@router.get("/drafts", summary="Curriculum drafts (newest first)", response_model=DraftList)
async def drafts(db: DB, learner: Learner) -> DraftList:
    return DraftList(drafts=[_draft_out(d) for d in await curriculum.list_drafts(db, learner.id)])


@router.post(
    "/drafts",
    summary="Propose a draft for one course section (deterministic, or via the routed local model)",
    response_model=DraftOut,
    status_code=201,
)
async def create_draft(body: DraftCreate, db: DB, learner: Learner, gateway: Gateway) -> DraftOut:
    if body.use_model:
        payload, call_id = await drafting.draft_with_model(
            db, gateway, learner.id, course=body.course, section=body.section
        )
        # a failed/absent model route leaves the deterministic draft: say so, in the origin and
        # as a visible note on the draft
        notes = (
            []
            if call_id
            else [
                curriculum.Problem(
                    "warning", "draft", "model route unavailable; this is the deterministic draft"
                )
            ]
        )
        d = await curriculum.create_draft(
            db,
            learner.id,
            course=body.course,
            section=body.section,
            payload=payload,
            origin="model" if call_id else "deterministic",
            model_call_id=call_id,
            notes=notes,
        )
    else:
        d = await curriculum.create_draft(db, learner.id, course=body.course, section=body.section)
    return _draft_out(d)


@router.get("/drafts/{draft_id}", summary="One draft with its validation", response_model=DraftOut)
async def get_draft(draft_id: str, db: DB, learner: Learner) -> DraftOut:
    return _draft_out(await curriculum.get_draft(db, learner.id, draft_id))


@router.put(
    "/drafts/{draft_id}",
    summary="Replace the draft payload (re-validated; version +1)",
    response_model=DraftOut,
)
async def update_draft(draft_id: str, body: DraftUpdate, db: DB, learner: Learner) -> DraftOut:
    return _draft_out(
        await curriculum.update_draft(db, learner.id, draft_id, body.payload.model_dump())
    )


@router.post(
    "/drafts/{draft_id}/publish",
    summary="Publish: skills, prerequisites, a new learning-object version, assessments",
    response_model=PublishOut,
)
async def publish(draft_id: str, db: DB, learner: Learner) -> PublishOut:
    rep = await curriculum.publish_draft(db, learner.id, draft_id)
    d = await curriculum.get_draft(db, learner.id, draft_id)
    return PublishOut(
        draft=_draft_out(d),
        skills=rep.skills,
        edges=rep.edges,
        learning_objects=rep.learning_objects,
        new_object_versions=rep.new_object_versions,
        assessments=rep.assessments,
    )


@router.post(
    "/drafts/{draft_id}/reject",
    summary="Reject a draft (kept for the record)",
    response_model=DraftOut,
)
async def reject(draft_id: str, db: DB, learner: Learner) -> DraftOut:
    return _draft_out(await curriculum.reject_draft(db, learner.id, draft_id))


# ----------------------------------------------------------------------------- source passages
def _file_route(chunk_id: str) -> str:
    return f"/api/curriculum/chunks/{chunk_id}/file"


@router.get(
    "/chunks/{chunk_id}",
    summary="A cited passage with neighbours and a guarded open link (citation viewer)",
    response_model=ChunkOut,
)
async def chunk(chunk_id: str, db: DB, settings: SettingsDep) -> ChunkOut:
    p = await curriculum.passage(db, chunk_id)
    if p is None:
        raise AppError("not_found", "this passage is no longer in the corpus", http_status=404)
    if p.uri.startswith(("http://", "https://")):
        open_url: str | None = p.uri
    elif curriculum.open_target(p.uri, settings.ingest_roots_resolved) is not None:
        open_url = _file_route(p.chunk_id) + curriculum.open_fragment(
            p.source_type, p.uri, p.t_start
        )
    else:
        open_url = None
    return ChunkOut(
        chunk_id=p.chunk_id,
        text=p.text,
        citation=p.citation,
        course=p.course,
        section=p.section,
        lecture=p.lecture,
        source_type=p.source_type,
        trust_tier=p.trust_tier,
        document_title=p.document_title,
        uri=p.uri,
        open_url=open_url,
        t_start=p.t_start,
        t_end=p.t_end,
        prev_text=p.prev_text,
        next_text=p.next_text,
    )


@router.get(
    "/chunks/{chunk_id}/file",
    summary="The original file behind a passage (only plain files under INGEST_ROOTS; Range-capable)",
    response_class=FileResponse,
)
async def chunk_file(chunk_id: str, db: DB, settings: SettingsDep) -> FileResponse:
    p = await curriculum.passage(db, chunk_id)
    if p is None:
        raise AppError("not_found", "this passage is no longer in the corpus", http_status=404)
    path = curriculum.open_target(p.uri, settings.ingest_roots_resolved)
    if path is None:
        raise AppError(
            "not_found", "the original is not a file under the configured ingest roots", 404
        )
    return FileResponse(path, filename=path.name)


# ----------------------------------------------------------------------------- content reports
class _Empty(BaseModel):
    pass


@router.post(
    "/reports",
    summary="Report a wrong source, explanation or grading (kept next to the evidence)",
    response_model=ReportOut,
    status_code=201,
)
async def report(body: ReportIn, db: DB, learner: Learner) -> ReportOut:
    r = await curriculum.file_report(
        db,
        learner.id,
        kind=body.kind,
        turn_id=body.turn_id,
        chunk_id=body.chunk_id,
        skill_id=body.skill_id,
        note=body.note,
        assessment_id=body.assessment_id,
    )
    return _report_out(r)


@router.get("/reports", summary="Open content reports", response_model=ReportList)
async def reports(db: DB, learner: Learner, status: str = "open") -> ReportList:
    rows = (
        await db.execute(
            select(ContentReport)
            .where(ContentReport.learner_id == learner.id, ContentReport.status == status)
            .order_by(ContentReport.created_at.desc())
        )
    ).scalars()
    return ReportList(reports=[_report_out(r) for r in rows])


@router.post(
    "/reports/{report_id}/resolve", summary="Mark a report resolved", response_model=ReportOut
)
async def resolve(report_id: str, db: DB, learner: Learner) -> ReportOut:
    r = await db.get(ContentReport, report_id)
    if r is None or r.learner_id != learner.id:
        raise AppError("not_found", "report not found", http_status=404)
    r.status = "resolved"
    await db.commit()
    return _report_out(r)


def _report_out(r: ContentReport) -> ReportOut:
    return ReportOut(
        id=r.id,
        kind=r.kind,
        turn_id=r.turn_id,
        chunk_id=r.chunk_id,
        skill_id=r.skill_id,
        assessment_id=r.assessment_id,
        note=r.note,
        status=r.status,
        created_at=r.created_at,
    )
