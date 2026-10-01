from typing import Annotated

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db

router = APIRouter(tags=["system"])


class Health(BaseModel):
    status: str
    env: str
    db: str


@router.get("/health", summary="Liveness + DB connectivity", response_model=Health)
async def health(request: Request, db: Annotated[AsyncSession, Depends(get_db)]) -> Health:
    await db.execute(text("SELECT 1"))
    return Health(status="ok", env=request.app.state.settings.app_env, db="ok")
