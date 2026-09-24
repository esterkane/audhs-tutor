"""Bounded workspace context for explicit playground tutoring requests."""

from typing import Literal

from pydantic import BaseModel, Field


class PlaygroundMessage(BaseModel):
    role: Literal["user", "assistant"]
    text: str = Field(max_length=4000)


class PlaygroundRequest(BaseModel):
    session_id: str
    intent: Literal["chat", "explain", "hint", "big_picture"] = "chat"
    question: str = Field(default="", max_length=2000)
    exercise: str = Field(max_length=1000)
    code: str = Field(max_length=16000)
    output: str = Field(default="", max_length=4000)
    output_stale: bool = False
    history: list[PlaygroundMessage] = Field(default_factory=list, max_length=6)


class PlaygroundReply(BaseModel):
    text: str
    model: str
    route: str
    turn_id: str
    source_note: str = "General coding guidance; no course sources retrieved."
