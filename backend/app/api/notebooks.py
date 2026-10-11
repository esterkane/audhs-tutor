"""Local notebook setup, available only from the local application."""

from urllib.parse import urlsplit
from uuid import UUID

from fastapi import APIRouter, HTTPException, Request, Response
from pydantic import BaseModel, Field

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
