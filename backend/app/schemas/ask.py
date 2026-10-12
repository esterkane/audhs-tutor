"""Independent questions carry no implicit lesson/course/page context."""

from typing import Annotated, Any, cast

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    SerializerFunctionWrapHandler,
    StringConstraints,
    field_validator,
    model_serializer,
    model_validator,
)

from app.schemas.playground import PlaygroundReply


class AskSources(BaseModel):
    model_config = ConfigDict(extra="forbid")
    passage_ids: list[Annotated[str, StringConstraints(min_length=1, max_length=128)]] = Field(
        min_length=1, max_length=6
    )
    passage_hashes: dict[str, Annotated[str, StringConstraints(pattern=r"^[a-f0-9]{64}$")]] = Field(
        max_length=6
    )

    @model_validator(mode="after")
    def exact_selection(self) -> "AskSources":
        if len(set(self.passage_ids)) != len(self.passage_ids) or set(self.passage_ids) != set(
            self.passage_hashes
        ):
            raise ValueError("Choose distinct passages with their displayed-text hashes")
        return self


class AskQuestion(BaseModel):
    sources: AskSources | None = None

    @model_serializer(mode="wrap")
    def serialize(self, handler: SerializerFunctionWrapHandler) -> dict[str, Any]:
        data = cast(dict[str, Any], handler(self))
        if self.sources is None:
            data.pop("sources", None)  # Retain existing request fingerprints/retries.
        return data

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
