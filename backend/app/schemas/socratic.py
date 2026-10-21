"""A validated teaching-turn shape, not a factual correctness certificate."""

import re
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


def _prose(text: str) -> str:
    text = re.sub(r"`[^`\n]*`", "", text)
    return re.sub(r"https?://\S+", "", text)


class SocraticLessonReply(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    setup: str = Field(
        max_length=450,
        description=(
            "At most two factual setup sentences, no question or answer to the final question. "
            "A different worked example may be used."
        ),
    )
    question: str = Field(
        min_length=12,
        max_length=350,
        description=(
            "Exactly one answerable narrowing question using fresh inputs; do not supply its answer."
        ),
    )

    @model_validator(mode="after")
    def teaching_shape(self) -> "SocraticLessonReply":
        setup, question = _prose(self.setup), _prose(self.question)
        sentences = [part for part in re.split(r"(?<=[.!?])\s+", setup) if part.strip()]
        rendered = self.render()
        if (
            "?" in setup
            or len(sentences) > 2
            or question.count("?") != 1
            or not re.sub(r"(?:\s*\[\d+\])+\s*$", "", question).rstrip().endswith("?")
            or re.search(r"(?m)^\s*#{1,6}\s+", rendered)
            or "```" in rendered
            or re.search(r"</?[A-Za-z_]+>", rendered)
        ):
            raise ValueError(
                "Use at most two setup sentences without questions or headings, "
                "then exactly one question; no extra question or closing statement."
            )
        return self

    def render(self) -> str:
        return "\n\n".join(part for part in (self.setup, self.question) if part)


class SocraticLessonQuestionReply(SocraticLessonReply):
    """No unsolicited correction before a learner's follow-up question."""

    setup: Literal[""] = ""

    @model_validator(mode="after")
    def one_question_sentence(self) -> "SocraticLessonQuestionReply":
        if re.search(r"[.!]\s+", _prose(self.question)):
            raise ValueError("Ask one question; do not prepend an explanation or correction.")
        return self


class SocraticLessonProbe(BaseModel):
    """One neutral open probe; premises still require semantic quality evaluation."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    situation: str = Field(
        min_length=4,
        max_length=240,
        description=(
            "Only concrete inputs and the operation to investigate, without its result, "
            "correction, error name or conclusion. Use a short noun phrase; keep requested "
            "literal inputs."
        ),
    )
    focus: Literal["outcome", "comparison"]

    @model_validator(mode="after")
    def one_input_phrase(self) -> "SocraticLessonProbe":
        prose = _prose(self.situation)
        if (
            "?" in prose
            or "\n" in self.situation
            or "```" in self.situation
            or re.search(r"[.!]\s+|</?[A-Za-z_]+>", prose)
        ):
            raise ValueError(
                "Use one short input/operation phrase, not an explanation, question or instruction."
            )
        return self

    def render(self) -> str:
        question = (
            "what result would you expect"
            if self.focus == "outcome"
            else "what is the key difference"
        )
        return f"For {self.situation.rstrip('. ')}, {question}?"
