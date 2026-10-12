"""Independent questions carry no implicit lesson/course/page context."""

from pydantic import BaseModel, Field, field_validator

from app.schemas.playground import PlaygroundReply


class AskQuestion(BaseModel):
    question: str = Field(min_length=1, max_length=2000)
    area_id: str | None = Field(default=None, min_length=1, max_length=128)
    parent_answer_id: str | None = Field(default=None, min_length=1, max_length=128)

    @field_validator("question")
    @classmethod
    def nonempty(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Write a question first")
        return value


class AskReply(PlaygroundReply):
    conversation_id: str
    area_id: str | None = None
    parent_answer_id: str | None = None
    history_turns: int = 0
