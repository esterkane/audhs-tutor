"""Non-publishing structural review. Valid shape does not prove a correct lesson."""

import re
from typing import Annotated, Any

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    ValidationError,
    model_validator,
)

Text = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=12000)]


class Shape(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


def answer_text(value: str) -> str:
    """Mirror current deterministic grading without changing its accepted-answer policy."""
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9_√() ]+", " ", value.lower())).strip()


class MCQ(Shape):
    question: Text
    options: list[Text] = Field(min_length=2, max_length=12)
    answer: int = Field(ge=0)
    explanation: Text

    @model_validator(mode="after")
    def options_match(self) -> "MCQ":
        if self.answer >= len(self.options):
            raise ValueError("Correct option must be within the option list")
        normalized = [answer_text(option) for option in self.options]
        if not all(normalized) or len(set(normalized)) != len(self.options):
            raise ValueError("Options must remain nonempty and distinct under answer normalization")
        return self


class Cloze(Shape):
    text: Text
    answers: list[Text] = Field(min_length=1, max_length=20)

    @model_validator(mode="after")
    def usable_answers(self) -> "Cloze":
        # Match the current cloze grader's character normalization, without changing it.
        if any(not answer_text(answer) for answer in self.answers):
            raise ValueError("Accepted answers must survive the cloze grader's normalization")
        return self


class Explanation(Shape):
    prompt: Text


class Criterion(Shape):
    criterion: Text
    keywords: list[Text] = Field(default_factory=list, max_length=30)


class Rubric(Shape):
    criteria: list[Criterion] = Field(min_length=1, max_length=20)

    @model_validator(mode="after")
    def distinct(self) -> "Rubric":
        if len({row.criterion.casefold() for row in self.criteria}) != len(self.criteria):
            raise ValueError("Rubric criteria must be distinct")
        return self


class Challenge(Shape):
    prompt: Annotated[
        str, StringConstraints(strip_whitespace=True, min_length=20, max_length=12000)
    ]
    hidden_key: Annotated[
        str, StringConstraints(strip_whitespace=True, min_length=5, max_length=12000)
    ]
    criteria: list[Text] = Field(min_length=2, max_length=5)


EDITABLE: dict[str, type[Shape]] = {
    "mcq": MCQ,
    "cloze": Cloze,
    "explain_back": Explanation,
    "transfer": Explanation,
    **{
        f"challenge_{mode}": Challenge
        for mode in ("planted_error", "steelman", "teach_back", "calibration")
    },
}


def review(original: dict[str, Any], candidate: dict[str, Any]) -> list[dict[str, str]]:
    """Return field problems; never normalize or rewrite the stored candidate."""
    problems: list[dict[str, str]] = []

    def problem(field: str, message: str) -> None:
        problems.append({"field": field, "message": message})

    kind = original.get("kind")
    shape = EDITABLE.get(str(kind))
    if shape is None:
        problem(
            "kind",
            "Code correction requires execution review"
            if kind == "code"
            else "Unsupported question kind",
        )
        return problems
    if set(candidate) != {"item", "rubric"}:
        problem(
            "candidate",
            "Keep only the item and rubric fields; identity and ownership are server-owned",
        )
    item = candidate.get("item")
    old_item = original.get("item")
    if not isinstance(item, dict) or not isinstance(old_item, dict):
        problem("item", "Question content must be an object")
        return problems
    fields = set(shape.model_fields)
    if {key: value for key, value in item.items() if key not in fields} != {
        key: value for key, value in old_item.items() if key not in fields
    }:
        problem(
            "item",
            "Source links, clip settings and other non-editable metadata must remain unchanged",
        )
    try:
        shape.model_validate({key: value for key, value in item.items() if key in fields})
    except ValidationError as error:
        for detail in error.errors(include_input=False, include_url=False):
            problem("item." + ".".join(map(str, detail["loc"])), detail["msg"])
    rubric = candidate.get("rubric")
    if kind in {"mcq", "cloze"}:
        if rubric != original.get("rubric"):
            problem(
                "rubric", "This question uses deterministic grading; retain its original rubric"
            )
    else:
        try:
            parsed = Rubric.model_validate({"criteria": rubric})
            if str(kind).startswith("challenge_") and [
                row.criterion for row in parsed.criteria
            ] != item.get("criteria"):
                problem("rubric", "Challenge criteria and rubric must agree in the same order")
        except ValidationError as error:
            for detail in error.errors(include_input=False, include_url=False):
                problem("rubric." + ".".join(map(str, detail["loc"])), detail["msg"])
    return problems
