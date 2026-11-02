"""A bounded missing-question repair that cannot rewrite accepted explanation prose."""

import re
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator


class QuestionRepair(BaseModel):
    model_config = ConfigDict(extra="forbid")
    question: str = Field(min_length=8, max_length=1000)

    @model_validator(mode="after")
    def one_question(self) -> "QuestionRepair":
        if self.question.count("?") != 1 or not self.question.rstrip().endswith("?"):
            raise ValueError("Supply one complete application question ending in a question mark")
        if "```" in self.question:
            raise ValueError("The question must not contain a code or protocol block")
        return self


QUESTION_REPAIR_POLICY = (
    "HOST QUESTION-ONLY REPAIR: The previous explanation must remain unchanged. "
    "Return only the QuestionRepair object with one question. Do not repeat the explanation, "
    "return metadata, request tools or answer your own question. Ask a short application "
    "question grounded in the already explained mechanism, in the session language. "
    "Use a small changed condition that the explanation prepares the learner to reason about; "
    "do not merely ask them to repeat a value or fact just stated. Do not introduce unsupported "
    "premises. This output shape overrides full-answer repair and tutor footer instructions. "
    "The host will preserve the explanation and metadata and re-run all output guards."
)


def repaired_parts(turn: Any, repair: QuestionRepair) -> tuple[str, dict[str, Any]]:
    metadata = turn.model_dump(mode="json", exclude={"text", "guard_flags"})
    metadata["next_question"] = repair.question
    # Preserve every byte of the explanation and all other metadata, including speech.
    return turn.text + "\n\n" + repair.question, metadata


def compatible_speech(turn: Any) -> bool:
    # Keep the ordinary full repair when preserved speech explicitly declines a check.
    # Appending a question must not introduce a known contradictory voice summary.
    return (
        re.search(
            r"\b(?:no (?:quiz|questions?|check)|without (?:a )?(?:quiz|questions?)"
            r"|kein(?:e|en)? (?:quiz|fragen?|kontrollfragen?))\b",
            turn.speech,
            re.I,
        )
        is None
    )
