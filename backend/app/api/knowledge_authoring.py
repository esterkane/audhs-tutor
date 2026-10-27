"""Notes and uploads are inputs to editable, inactive knowledge drafts."""

import hashlib
from pathlib import Path
from typing import Annotated
from urllib.parse import unquote
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Header, Request
from sqlalchemy import select, text
from starlette.concurrency import run_in_threadpool

from app.api.curriculum import _draft_out
from app.api.deps import DB, Gateway, Learner, SettingsDep
from app.core.errors import AppError
from app.db.models import CurriculumDraft
from app.kernel import curriculum, knowledge_authoring
from app.kernel.learning_scope import reference_before, require_current_material
from app.knowledge.ingest.loaders import load_file
from app.knowledge.ingest.service import ingest_source
from app.schemas.curriculum import DraftOut
from app.schemas.knowledge_authoring import (
    KnowledgeMaterialInput,
    KnowledgeMaterialUpdate,
    KnowledgeReadingOut,
    KnowledgeSuggestIn,
    KnowledgeUploadOut,
    MemorySearchIn,
    MemorySearchOut,
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
    if suffix not in {".txt", ".md", ".pdf", ".docx"}:
        raise AppError("unsupported_upload", "Choose a TXT, Markdown, PDF or DOCX file.", 422)
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
        doc = await run_in_threadpool(load_file, path, uri=str(path))
    except Exception:
        raise AppError(
            "unreadable_upload", "Could not extract this file. Try a text export.", 422
        ) from None
    if not doc.text.strip():
        raise AppError("empty_upload", "No readable text found. Scanned PDFs need OCR first.", 422)
    if len(doc.text) > 120000:
        raise AppError(
            "upload_text_too_large",
            "Choose a smaller document or export a section (120,000 characters maximum).",
            422,
        )
    doc.title = name
    result = await ingest_source(db, doc, trust_tier=1, repo=None, dedupe=False)
    return KnowledgeUploadOut(
        document_id=result.document_id,
        filename=name,
        text=doc.text,
        sha256=digest,
        characters=len(doc.text),
    )


@router.post("/drafts", response_model=DraftOut)
async def create(
    body: KnowledgeMaterialInput,
    db: DB,
    learner: Learner,
    request_id: Annotated[UUID, Header(alias="Idempotency-Key")],
) -> DraftOut:
    fingerprint = hashlib.sha256(body.model_dump_json().encode()).hexdigest()
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
    command = KnowledgeMaterialInput.model_validate(body.model_dump(exclude={"expected_version"}))
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
async def accepted_reading(skill_id: str, db: DB, learner: Learner) -> KnowledgeReadingOut | None:
    from app.kernel import skill_graph

    node = await skill_graph.get_node(db, skill_id, learner_id=learner.id)
    draft = await db.scalar(
        select(CurriculumDraft)
        .where(
            CurriculumDraft.learner_id == learner.id,
            CurriculumDraft.origin == "knowledge_authored",
            CurriculumDraft.status == "published",
            CurriculumDraft.payload_json["skills"][0]["slug"].as_string() == node.slug,
        )
        .order_by(CurriculumDraft.published_at.desc())
        .limit(1)
    )
    if draft is None:
        return None
    lo = await skill_graph.learning_object_for(db, node.id, learner_id=learner.id)
    if lo is None:
        return None
    examples = list(lo.examples_json or [])
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
    )


async def _current_draft(db: DB, learner_id: str, draft_id: str) -> CurriculumDraft:
    draft = await curriculum.get_draft(db, learner_id, draft_id)
    await require_current_material(db, learner_id, draft.created_at)
    return draft
