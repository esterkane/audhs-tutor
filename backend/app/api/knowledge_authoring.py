"""Notes and uploads are inputs to editable, inactive knowledge drafts."""

import hashlib
from pathlib import Path
from typing import Annotated
from urllib.parse import unquote
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Header, Query, Request
from fastapi.responses import Response
from sqlalchemy import func, select, text
from starlette.concurrency import run_in_threadpool

from app.api.curriculum import _draft_out
from app.api.deps import DB, Gateway, Learner, SettingsDep
from app.core.errors import AppError
from app.db.models import CurriculumDraft, Document, DocumentVersion, LearningObject, SkillNode
from app.kernel import curriculum, knowledge_authoring
from app.kernel.content_access import skill_visible
from app.kernel.learning_scope import reference_before, require_current_material
from app.knowledge import pdf_page_preview, pdf_page_sources
from app.knowledge.ingest.loaders import load_file
from app.knowledge.ingest.pdf_ocr import PdfOcrError, PdfOcrOptions
from app.knowledge.ingest.service import ingest_source
from app.schemas.curriculum import DraftOut
from app.schemas.knowledge_authoring import (
    AcceptedPdfSource,
    KnowledgeMaterialInput,
    KnowledgeMaterialUpdate,
    KnowledgeReadingOut,
    KnowledgeSuggestIn,
    KnowledgeUploadOut,
    MemorySearchIn,
    MemorySearchOut,
    PdfPageSources,
    ResearchTutorIn,
    ResearchTutorOut,
)

router = APIRouter(prefix="/knowledge-material", tags=["knowledge-material"])


@router.post("/drafts/{draft_id}/memories/search", response_model=MemorySearchOut)
async def search_memories(
    draft_id: str,
    body: MemorySearchIn,
    db: DB,
    learner: Learner,
    request: Request,
    background: BackgroundTasks,
    settings: SettingsDep,
) -> MemorySearchOut:
    import asyncio

    from app.knowledge import personal_memory
    from app.knowledge.reindex import build_repo, embed_spec

    await _current_draft(db, learner.id, draft_id)
    if not body.query.strip():
        return MemorySearchOut(memories=[])
    lock = getattr(request.app.state, "personal_memory_lock", None)
    if lock is None:
        lock = asyncio.Lock()
        request.app.state.personal_memory_lock = lock
    async with lock:
        try:
            # A separate model-specific collection never contaminates the source corpus.
            spec = await embed_spec(db, settings)
            identity = hashlib.sha256(spec.model_dump_json().encode()).hexdigest()[:16]
            repo = getattr(request.app.state, "personal_repo", None)
            if repo is None or getattr(request.app.state, "personal_model", None) != identity:
                repo = await build_repo(db, settings, collection="personal_" + identity)
                request.app.state.personal_repo = repo
                request.app.state.personal_model = identity
            memories = await personal_memory.search(db, repo, learner.id, draft_id, body.query)
        except AppError:
            raise
        except Exception as exc:
            raise AppError(
                "memory_unavailable",
                "Earlier notes could not be searched locally. "
                "Your writing is saved; you can continue without retrieval.",
                503,
            ) from exc
    # Deliver retrieval first, then restore tutor weights while the learner reviews notes.
    from app.api.tutor_preparation import schedule_research_preparation

    schedule_research_preparation(request, background, settings, learner.id, draft_id)
    return MemorySearchOut(memories=memories)


@router.post("/drafts/{draft_id}/prepare-tutor", status_code=202)
async def prepare_research_tutor(
    draft_id: str,
    db: DB,
    learner: Learner,
    request: Request,
    background: BackgroundTasks,
    settings: SettingsDep,
) -> dict[str, str]:
    from app.api.tutor_preparation import schedule_research_preparation

    draft = await _current_draft(db, learner.id, draft_id)
    if draft.status == "draft":
        schedule_research_preparation(request, background, settings, learner.id, draft_id)
    return {"status": "accepted"}


@router.post("/drafts/{draft_id}/research-tutor", response_model=ResearchTutorOut)
async def research_tutor(
    draft_id: str,
    body: ResearchTutorIn,
    db: DB,
    gateway: Gateway,
    learner: Learner,
    request: Request,
    settings: SettingsDep,
) -> ResearchTutorOut:
    await _current_draft(db, learner.id, draft_id)
    from app.orchestrator.research_tutor import help_research

    request.app.state.research_tutor_active = (
        getattr(request.app.state, "research_tutor_active", 0) + 1
    )
    try:
        draft, reused = await help_research(db, gateway, learner.id, draft_id, body, settings)
        return ResearchTutorOut(**_draft_out(draft).model_dump(), reused=reused)
    finally:
        request.app.state.research_tutor_active -= 1


@router.post("/drafts/{draft_id}/research-questions", response_model=DraftOut)
async def research_questions(
    draft_id: str,
    body: KnowledgeSuggestIn,
    db: DB,
    gateway: Gateway,
    learner: Learner,
    settings: SettingsDep,
) -> DraftOut:
    await _current_draft(db, learner.id, draft_id)
    from app.orchestrator.knowledge_authoring import suggest_research_questions

    draft = await suggest_research_questions(
        db, gateway, learner.id, draft_id, body.expected_version, settings
    )
    return _draft_out(draft)


@router.post("/uploads", response_model=KnowledgeUploadOut)
async def upload(
    request: Request,
    db: DB,
    learner: Learner,
    settings: SettingsDep,
    filename: Annotated[str, Header(alias="X-Filename", max_length=2000)],
) -> KnowledgeUploadOut:
    name = Path(unquote(filename).replace("\\", "/")).name
    suffix = Path(name).suffix.lower()
    if suffix not in {".txt", ".md", ".pdf", ".docx", ".ipynb"}:
        raise AppError(
            "unsupported_upload",
            "Choose a TXT, Markdown, PDF, DOCX or Jupyter notebook (.ipynb).",
            422,
        )
    content = bytearray()
    async for block in request.stream():
        if len(content) + len(block) > 10 * 1024 * 1024:
            raise AppError("upload_too_large", "Upload limit is 10 MiB.", 413)
        content.extend(block)
    if not content:
        raise AppError("empty_upload", "The file is empty.", 422)
    digest = hashlib.sha256(content).hexdigest()
    storage_root = await run_in_threadpool(Path(settings.knowledge_authoring_root).expanduser)
    if not storage_root.is_absolute():
        storage_root = settings.project_root / storage_root
    folder = storage_root / "knowledge-authoring" / learner.id
    cutoff = await reference_before(db, learner.id)
    if cutoff is not None:
        folder = folder / hashlib.sha256(cutoff.encode()).hexdigest()[:16]
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / (digest + suffix)
    if not path.exists():
        path.write_bytes(content)
    try:
        ocr = (
            PdfOcrOptions(
                languages=settings.pdf_ocr_languages,
                max_pages=settings.pdf_ocr_max_pages,
                timeout_s=settings.pdf_ocr_timeout_s,
            )
            if settings.pdf_ocr_enabled
            else None
        )
        doc = await run_in_threadpool(
            load_file,
            path,
            uri=str(path),
            pdf_ocr=ocr,
            pdf_ocr_required=True,
            notebook_source_only=True,
        )
    except PdfOcrError as exc:
        raise AppError(exc.code, str(exc), 422) from None
    except Exception:
        raise AppError(
            "unreadable_upload", "Could not extract this file. Try a text export.", 422
        ) from None
    # A successfully inspected image page is usable as a visual source for manual notes.
    visual_pdf = suffix == ".pdf" and doc.meta.get("pdf_extraction", {}).get("visual_pages")
    if not doc.text.strip() and not visual_pdf:
        raise AppError(
            "empty_upload", "No readable text found. Try clearer pages or a text export.", 422
        )
    if len(doc.text) > 120000:
        raise AppError(
            "upload_text_too_large",
            "Choose a smaller document or export a section (120,000 characters maximum).",
            422,
        )
    if suffix == ".pdf":
        doc.content_hash = await run_in_threadpool(
            pdf_page_sources.persist, path, digest, doc, settings.pdf_ocr_languages
        )
    doc.title = name
    result = await ingest_source(db, doc, trust_tier=1, repo=None, dedupe=False)
    return KnowledgeUploadOut(
        document_id=result.document_id,
        document_version_id=result.version_id if suffix == ".pdf" else None,
        filename=name,
        text=doc.text,
        sha256=digest,
        characters=len(doc.text),
        ocr_pages=doc.meta.get("pdf_extraction", {}).get("ocr_pages", []),
        ocr_empty_pages=doc.meta.get("pdf_extraction", {}).get("empty_ocr_pages", []),
    )


async def owned_pdf_version(
    upload_id: str, version_id: str, db: DB, learner: Learner, settings: SettingsDep
) -> tuple[Path, Path, str]:
    doc = await db.get(Document, upload_id)
    version = await db.get(DocumentVersion, version_id)
    if (
        doc is None
        or doc.source_type != "pdf"
        or version is None
        or version.document_id != doc.id
        or f"/knowledge-authoring/{learner.id}/" not in doc.uri
    ):
        raise AppError("not_found", "The PDF extraction is unavailable.", 404)
    await require_current_material(db, learner.id, doc.created_at)
    storage = await run_in_threadpool(Path(settings.knowledge_authoring_root).expanduser)
    owner = settings.project_root / storage / "knowledge-authoring" / learner.id
    return Path(doc.uri), owner, version.content_hash


@router.get("/uploads/{upload_id}/versions/{version_id}/pages", response_model=PdfPageSources)
async def pdf_pages(
    upload_id: str, version_id: str, db: DB, learner: Learner, settings: SettingsDep
) -> PdfPageSources:
    source = await owned_pdf_version(upload_id, version_id, db, learner, settings)
    return await run_in_threadpool(pdf_page_sources.read, *source)


@router.get(
    "/uploads/{upload_id}/versions/{version_id}/pages/{page}/preview",
    response_class=Response,
    responses={200: {"content": {"image/png": {}}}},
)
async def preview_pdf_page(
    upload_id: str, version_id: str, page: int, db: DB, learner: Learner, settings: SettingsDep
) -> Response:
    source = await owned_pdf_version(upload_id, version_id, db, learner, settings)
    png = await run_in_threadpool(pdf_page_preview.render, *source, page)
    return Response(
        png,
        media_type="image/png",
        headers={
            "Cache-Control": "private, no-store",
            "X-Content-Type-Options": "nosniff",
        },
    )


@router.post("/drafts", response_model=DraftOut)
async def create(
    body: KnowledgeMaterialInput,
    db: DB,
    learner: Learner,
    request_id: Annotated[UUID, Header(alias="Idempotency-Key")],
) -> DraftOut:
    # Preserve fingerprints of requests created before optional reading questions existed.
    empty_prequestions = {
        key
        for key in ("explanation_prequestion", "worked_example_prequestion")
        if getattr(body, key) == ""
    }
    if body.relationship is None:
        empty_prequestions.add("relationship")
    if body.case_comparison is None:
        empty_prequestions.add("case_comparison")
    if body.upload_version_id is None:
        empty_prequestions.add("upload_version_id")
    fingerprint = hashlib.sha256(
        body.model_dump_json(exclude=empty_prequestions).encode()
    ).hexdigest()
    await db.execute(text("BEGIN IMMEDIATE"))
    prior = await db.scalar(
        select(CurriculumDraft).where(
            CurriculumDraft.learner_id == learner.id,
            CurriculumDraft.payload_json["authoring"]["request_id"].as_string() == str(request_id),
        )
    )
    if prior:
        if prior.payload_json["authoring"]["request_fingerprint"] != fingerprint:
            raise AppError(
                "authoring_conflict", "This save identity belongs to different content.", 409
            )
        return _draft_out(prior)
    payload = await knowledge_authoring.payload_for(
        db,
        learner.id,
        body,
        "knowledge-" + request_id.hex,
        {"request_id": str(request_id), "request_fingerprint": fingerprint},
    )
    return _draft_out(
        await curriculum.create_draft(
            db,
            learner.id,
            course=None,
            section=None,
            payload=payload,
            origin="knowledge_authored",
            area_id=payload.get("area_id"),
        )
    )


@router.put("/drafts/{draft_id}", response_model=DraftOut)
async def update(
    draft_id: str, body: KnowledgeMaterialUpdate, db: DB, learner: Learner
) -> DraftOut:
    draft = await _current_draft(db, learner.id, draft_id)
    previous = draft.payload_json.get("authoring")
    if not previous:
        raise AppError("invalid_authoring_draft", "Choose a knowledge material draft.", 422)
    fields = body.model_dump(exclude={"expected_version"})
    for field in (
        "case_comparison",
        "relationship",
        "explanation_prequestion",
        "worked_example_prequestion",
    ):
        if field not in body.model_fields_set and field in previous:
            fields[field] = previous[field]
    command = KnowledgeMaterialInput.model_validate(fields)
    if previous.get("factual_review_id") and not previous.get("skill_slug"):
        # Recover review drafts saved before the original skill identity was retained.
        parent = await curriculum.get_draft(db, learner.id, previous["revised_from_draft_id"])
        previous = {**previous, "skill_slug": parent.payload_json["skills"][0]["slug"]}
    payload = await knowledge_authoring.payload_for(
        db,
        learner.id,
        command,
        previous.get("skill_slug", "knowledge-" + UUID(previous["request_id"]).hex),
        previous,
    )
    saved = await curriculum.update_draft(
        db, learner.id, draft_id, payload, expected_version=body.expected_version
    )
    saved.title = body.title
    await db.commit()
    return _draft_out(saved)


@router.post("/drafts/{draft_id}/suggest", response_model=DraftOut)
async def suggest(
    draft_id: str,
    body: KnowledgeSuggestIn,
    db: DB,
    learner: Learner,
    gateway: Gateway,
    settings: SettingsDep,
) -> DraftOut:
    await _current_draft(db, learner.id, draft_id)
    from app.orchestrator.knowledge_authoring import suggest_material

    return _draft_out(
        await suggest_material(db, gateway, learner.id, draft_id, body.expected_version, settings)
    )


@router.post("/drafts/{draft_id}/revise", response_model=DraftOut)
async def revise(
    draft_id: str,
    body: KnowledgeSuggestIn,
    db: DB,
    learner: Learner,
    request_id: Annotated[UUID, Header(alias="Idempotency-Key")],
) -> DraftOut:
    await _current_draft(db, learner.id, draft_id)
    original = await curriculum.get_draft(db, learner.id, draft_id)
    if (
        original.status != "published"
        or original.version != body.expected_version
        or not original.payload_json.get("authoring")
    ):
        raise AppError(
            "authoring_changed", "Choose the latest active knowledge material to revise.", 409
        )
    fingerprint = hashlib.sha256(f"{draft_id}:{body.expected_version}".encode()).hexdigest()
    await db.commit()
    await db.execute(text("BEGIN IMMEDIATE"))
    prior = await db.scalar(
        select(CurriculumDraft).where(
            CurriculumDraft.learner_id == learner.id,
            CurriculumDraft.payload_json["authoring"]["request_id"].as_string() == str(request_id),
        )
    )
    if prior:
        if prior.payload_json["authoring"]["request_fingerprint"] != fingerprint:
            raise AppError(
                "authoring_conflict", "Save identity belongs to different material.", 409
            )
        return _draft_out(prior)
    import copy

    payload = copy.deepcopy(original.payload_json)
    slug = payload["skills"][0]["slug"]
    payload["authoring"].update(
        request_id=str(request_id),
        request_fingerprint=fingerprint,
        skill_slug=slug,
        revised_from_draft_id=draft_id,
    )
    return _draft_out(
        await curriculum.create_draft(
            db,
            learner.id,
            course=None,
            section=None,
            payload=payload,
            origin="knowledge_authored",
            area_id=payload.get("area_id"),
        )
    )


@router.get("/skills/{skill_id}/reading", response_model=KnowledgeReadingOut | None)
async def accepted_reading(
    skill_id: str, db: DB, learner: Learner, settings: SettingsDep
) -> KnowledgeReadingOut | None:
    from app.kernel import skill_graph

    node = await skill_graph.get_node(db, skill_id, learner_id=learner.id)
    draft = await curriculum.latest_accepted_material(db, learner.id, node.slug)
    if draft is None:
        return None
    lo = await skill_graph.learning_object_for(db, node.id, learner_id=learner.id)
    if lo is None:
        return None
    reading = _reading_view(node, draft, lo)
    accepted = draft.payload_json.get("authoring", {})
    upload_id, version_id = accepted.get("upload_id"), accepted.get("upload_version_id")
    if (
        isinstance(upload_id, str)
        and isinstance(version_id, str)
        and [reading.explanation, reading.worked_example]
        == [accepted.get("explanation"), accepted.get("worked_example")]
    ):
        try:
            await owned_pdf_version(upload_id, version_id, db, learner, settings)
        except AppError as exc:
            if exc.code not in {"not_found", "accuracy_review_only"}:
                raise
        else:
            reading.original_pdf = AcceptedPdfSource(upload_id=upload_id, version_id=version_id)
    return reading


def _reading_view(
    node: SkillNode, draft: CurriculumDraft, lo: LearningObject
) -> KnowledgeReadingOut:
    examples = list(lo.examples_json or [])
    authoring = draft.payload_json.get("authoring", {})
    original_examples = [authoring.get("explanation"), authoring.get("worked_example")]
    relationship = (
        knowledge_authoring.accepted_relationship(authoring.get("relationship"))
        if list(examples[:2]) == original_examples
        else None
    )
    return KnowledgeReadingOut(
        draft_id=draft.id,
        title=node.title,
        objective=lo.goal,
        explanation=str(examples[0]) if examples else "",
        worked_example=str(examples[1]) if len(examples) > 1 else "",
        question=str((lo.exercises_json or [""])[0]),
        notes=str(draft.payload_json.get("authoring", {}).get("notes", "")),
        sources=list(lo.sources_json or []),
        learning_object_version=lo.version,
        relationship=relationship,
        case_comparison=knowledge_authoring.accepted_case_comparison(
            draft.payload_json.get("authoring", {}).get("case_comparison")
        ),
        prequestions=knowledge_authoring.accepted_prequestions(
            draft.payload_json.get("authoring", {}),
            str(examples[0]) if examples else "",
            str(examples[1]) if len(examples) > 1 else "",
        ),
    )


@router.get("/library/lesson-matches", response_model=list[str])
async def library_lesson_matches(
    db: DB, learner: Learner, q: Annotated[str, Query(min_length=1, max_length=200)]
) -> list[str]:
    """Search the same accepted reading the learner can open, returning only matching skill IDs."""
    slug = CurriculumDraft.payload_json["skills"][0]["slug"].as_string()
    ranked = (
        curriculum.visible_accepted_material(learner.id)
        .with_only_columns(
            CurriculumDraft.id,
            slug.label("slug"),
            func.row_number()
            .over(
                partition_by=slug,
                order_by=(CurriculumDraft.published_at.desc(), CurriculumDraft.id.desc()),
            )
            .label("position"),
        )
        .subquery()
    )
    current_object_id = (
        select(LearningObject.id)
        .where(LearningObject.skill_id == SkillNode.id)
        .order_by(LearningObject.version.desc())
        .limit(1)
        .correlate(SkillNode)
        .scalar_subquery()
    )
    rows = await db.execute(
        select(SkillNode, CurriculumDraft, LearningObject)
        .select_from(SkillNode)
        .join(ranked, (ranked.c.slug == SkillNode.slug) & (ranked.c.position == 1))
        .join(CurriculumDraft, CurriculumDraft.id == ranked.c.id)
        .join(LearningObject, LearningObject.id == current_object_id)
        .where(skill_visible(learner.id))
    )
    term = q.casefold()
    matches = []
    for node, draft, lo in rows:
        view = _reading_view(node, draft, lo)
        fields = [view.objective, view.notes, view.explanation, view.worked_example, view.question]
        fields.extend(item.question for item in view.prequestions)
        if view.case_comparison:
            fields.extend([view.case_comparison.case_a, view.case_comparison.case_b])
        if any(term in field.casefold() for field in fields):
            matches.append(node.id)
    return matches


async def _current_draft(db: DB, learner_id: str, draft_id: str) -> CurriculumDraft:
    draft = await curriculum.get_draft(db, learner_id, draft_id)
    await require_current_material(db, learner_id, draft.created_at)
    return draft
