"""Bounded workspace context for explicit playground tutoring requests."""

from typing import Literal, Self

from pydantic import BaseModel, Field, model_validator


class PlaygroundMessage(BaseModel):
    role: Literal["user", "assistant"]
    text: str = Field(max_length=4000)


class PlaygroundContext(BaseModel):
    """Client supplied navigation identity, not a verified retrieval/source claim."""

    course_id: str | None = Field(default=None, min_length=1, max_length=200)
    section_id: str | None = Field(default=None, min_length=1, max_length=200)
    target_id: str | None = Field(default=None, min_length=1, max_length=1000)
    target_label: str | None = Field(default=None, max_length=300)


class PlaygroundRequest(BaseModel):
    session_id: str
    prefer_saved: bool = False
    questioning_style: Literal["explicit", "socratic"] = "explicit"
    learning_context: PlaygroundContext | None = None
    learner_question: str | None = Field(default=None, max_length=2000)
    learner_answer: str | None = Field(default=None, max_length=8000)
    intent: Literal["chat", "explain", "hint", "big_picture", "check_answer"] = "chat"
    question: str = Field(default="", max_length=2000)
    exercise: str = Field(max_length=8000)
    code: str = Field(max_length=16000)
    output: str = Field(default="", max_length=4000)
    output_stale: bool = False
    history: list[PlaygroundMessage] = Field(default_factory=list, max_length=6)

    @model_validator(mode="after")
    def check_requires_answer(self) -> Self:
        if self.intent == "check_answer" and not (self.learner_answer or "").strip():
            raise ValueError("Write an answer before requesting feedback")
        return self


class PlaygroundReply(BaseModel):
    text: str
    model: str
    route: str
    turn_id: str
    answer_id: str | None = None
    save_error: str | None = None
    save_receipt: str | None = None
    reused: bool = False
    saved_at: str | None = None
    memory_answers: list[str] = Field(default_factory=list)
    source_note: str = "General coding guidance; no course sources retrieved."
