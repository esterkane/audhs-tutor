"""Read-only recovery of a voice request; never a playback or inference command."""

from typing import Literal

from pydantic import BaseModel

from app.schemas.tutor import TurnDone


class VoiceResultOut(BaseModel):
    request_id: str
    status: Literal["not_found", "unresolved", "completed", "partial"]
    transcript: str | None = None
    text: str | None = None
    turn: TurnDone | None = None
    interrupted: bool = False
