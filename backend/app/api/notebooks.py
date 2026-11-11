"""Local notebook setup, available only from the local application."""

import asyncio
import re
from pathlib import Path
from urllib.parse import urlsplit
from uuid import UUID

from fastapi import APIRouter, HTTPException, Request, Response
from fastapi.responses import PlainTextResponse, RedirectResponse
from pydantic import BaseModel, Field

from app.api.deps import DB, Learner, SettingsDep
from app.core.errors import AppError
from app.db.models import Document
from app.notebooks.edits import saved_edits
from app.notebooks.inspection import NotebookInspection, inspect_notebook
from app.notebooks.lab import NotebookLab

router = APIRouter(prefix="/notebooks", tags=["notebooks"])


class StartNotebook(BaseModel):
    course_id: str = Field(min_length=1, max_length=100, pattern=r"^[a-zA-Z0-9_-]+$")
    install: bool = False
    request_id: UUID | None = None
    service_id: UUID | None = None


class NotebookStatus(BaseModel):
    status: str
    message: str
    url: str | None
    course_id: str
    request_id: str | None = None
    service_id: str | None = None


def local(request: Request) -> NotebookLab:
    allowed = {"127.0.0.1", "localhost", "::1", "testserver"}
    if request.url.hostname not in allowed or (
        request.client and request.client.host not in allowed
    ):
        raise HTTPException(403, "Notebook control is local-only.")
    origin = request.headers.get("origin")
    if origin and urlsplit(origin).hostname not in {"127.0.0.1", "localhost", "::1"}:
        raise HTTPException(403, "Notebook control requires a local application origin.")
    return request.app.state.notebook_lab  # type: ignore[no-any-return]


class NotebookUploadAvailability(BaseModel):
    available: bool


async def owned_upload(
    document_id: str, db: DB, learner: Learner, settings: SettingsDep
) -> Path | None:
    if not re.fullmatch(r"[0-7][0-9A-HJKMNP-TV-Z]{25}", document_id):
        return None
    doc = await db.get(Document, document_id)
    if doc is None or doc.source_type != "notebook":
        return None
    return await asyncio.to_thread(validated_source, doc.uri, learner.id, settings)


def validated_source(uri: str, learner_id: str, settings: SettingsDep) -> Path | None:
    storage = settings.project_root / Path(settings.knowledge_authoring_root).expanduser()
    owner = storage / "knowledge-authoring" / learner_id
    path = Path(uri)
    if not path.is_relative_to(owner) or path.resolve() != path or not path.is_file():
        return None
    parts = path.relative_to(owner).parts
    if len(parts) == 2 and not re.fullmatch("[0-9a-f]{16}", parts[0]):
        return None
    if len(parts) not in {1, 2} or not re.fullmatch(r"[0-9a-f]{64}\.ipynb", path.name):
        return None
    return path


@router.get("/uploads/{document_id}", response_model=NotebookUploadAvailability)
async def upload_availability(
    document_id: str,
    request: Request,
    response: Response,
    db: DB,
    learner: Learner,
    settings: SettingsDep,
) -> NotebookUploadAvailability:
    local(request)
    response.headers["Cache-Control"] = "no-store"
    return NotebookUploadAvailability(
        available=await owned_upload(document_id, db, learner, settings) is not None
    )


@router.get("/uploads/{document_id}/edits", response_model=list[str])
async def upload_edits(
    document_id: str,
    request: Request,
    response: Response,
    db: DB,
    learner: Learner,
    settings: SettingsDep,
) -> list[str]:
    local(request)
    response.headers["Cache-Control"] = "no-store"
    path = await owned_upload(document_id, db, learner, settings)
    if path is None:
        raise HTTPException(404, "The original notebook is unavailable.")
    try:
        return await asyncio.to_thread(saved_edits, path, settings.project_root, document_id)
    except (OSError, ValueError, RecursionError) as exc:
        raise HTTPException(
            422, "Could not read the saved notebook. Check its format and size."
        ) from exc


@router.post("/uploads/{document_id}/start", response_model=NotebookStatus)
async def start_upload(
    document_id: str,
    body: StartNotebook,
    request: Request,
    response: Response,
    db: DB,
    learner: Learner,
    settings: SettingsDep,
) -> NotebookStatus:
    lab = local(request)
    if request.headers.get("x-notebook-action") != "start":
        raise HTTPException(403, "Use the notebook setup button in the local app.")
    if (
        body.course_id != f"upload-{document_id}"
        or body.service_id is None
        or body.request_id is None
    ):
        raise HTTPException(422, "Notebook, request and backend identities must match.")
    path = await owned_upload(document_id, db, learner, settings)
    if path is None:
        raise AppError("notebook_upload_unavailable", "The original notebook is unavailable.", 404)
    response.headers["Cache-Control"] = "no-store"
    return NotebookStatus.model_validate(
        lab.start_command(
            str(body.service_id), str(body.request_id), body.course_id, body.install, upload=path
        )
    )


@router.get(
    "/open/{service_id}/{request_id}",
    response_class=RedirectResponse,
    status_code=303,
    responses={409: {"description": "The prepared notebook is no longer available."}},
)
async def open_notebook(service_id: UUID, request_id: UUID, request: Request) -> Response:
    lab = local(request)
    headers = {"Cache-Control": "no-store", "Referrer-Policy": "no-referrer"}
    if request.headers.get("sec-fetch-site") not in {None, "same-origin", "none"}:
        return PlainTextResponse(
            "Open the prepared notebook from the local tutor.", status_code=403, headers=headers
        )
    try:
        destination = await lab.launch_url(str(service_id), str(request_id))
    except AppError as error:
        return PlainTextResponse(
            "This notebook link is unavailable. Return to the tutor and prepare the notebook again.",
            status_code=error.http_status,
            headers=headers,
        )
    return RedirectResponse(destination, status_code=303, headers=headers)


@router.get("/status", response_model=NotebookStatus, summary="Read local notebook setup status")
async def status(request: Request, response: Response) -> NotebookStatus:
    lab = local(request)
    response.headers["Cache-Control"] = "no-store"
    return NotebookStatus.model_validate(lab.snapshot())


@router.get("/requests/{request_id}", response_model=NotebookStatus)
async def request_status(
    request_id: UUID, service_id: UUID, request: Request, response: Response
) -> NotebookStatus:
    response.headers["Cache-Control"] = "no-store"
    return NotebookStatus.model_validate(local(request).lookup(str(service_id), str(request_id)))


@router.post(
    "/start",
    response_model=NotebookStatus,
    summary="Prepare and start local notebook lab without executing cells",
)
async def start(body: StartNotebook, request: Request, response: Response) -> NotebookStatus:
    lab = local(request)
    if request.headers.get("x-notebook-action") != "start":
        raise HTTPException(403, "Use the notebook setup button in the local app.")
    if (body.request_id is None) != (body.service_id is None):
        raise HTTPException(422, "Both request and backend identities are required.")
    if body.request_id is not None and body.service_id is not None:
        response.headers["Cache-Control"] = "no-store"
        return NotebookStatus.model_validate(
            lab.start_command(
                str(body.service_id), str(body.request_id), body.course_id, body.install
            )
        )
    lab.start(body.course_id, body.install)
    return await status(request, response)


@router.get(
    "/check",
    response_model=NotebookInspection,
    summary="Inspect prepared notebook requirements without running cells",
)
async def check(course_id: str, request: Request, response: Response) -> NotebookInspection:
    lab = local(request)
    response.headers["Cache-Control"] = "no-store"
    return await inspect_notebook(lab.root, course_id, lab.env)
