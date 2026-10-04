"""Model proposes data/task; application owns the unfinished Python scaffold."""

import json
from typing import Any, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

VERSION = "starter.scaffold.v1"


def sample_value(text: str) -> Any:
    def reject_constant(value: str) -> None:
        raise ValueError("Use finite JSON values")

    try:
        value = json.loads(text, parse_constant=reject_constant)
    except (ValueError, RecursionError) as exc:
        raise ValueError("example_json must contain bounded valid JSON") from exc
    count = 0

    def visit(item: Any, depth: int) -> None:
        nonlocal count
        count += 1
        if depth > 6 or count > 200:
            raise ValueError("Use a small example with at most200 values and6 nesting levels")
        if isinstance(item, (list, dict)):
            for child in item.values() if isinstance(item, dict) else item:
                visit(child, depth + 1)
        elif isinstance(item, float):
            import math

            if not math.isfinite(item):
                raise ValueError("Use finite JSON values")

    visit(value, 0)
    return value


class StarterPlan(BaseModel):
    model_config = ConfigDict(extra="forbid")
    explanation: str = Field(min_length=1, max_length=1200)
    result_description: str = Field(
        min_length=10,
        max_length=600,
        description=(
            "Describe the value practice(data) should return, including required data keys. "
            "Not instructions to create a function or a task."
        ),
    )
    example_json: str = Field(min_length=1, max_length=2000)

    @model_validator(mode="after")
    def bounded_data_only(self) -> Self:
        sample_value(self.example_json)
        if not self.explanation.strip() or not self.result_description.strip():
            raise ValueError("Provide a nonempty explanation and learner task")
        if any(
            term in self.result_description.casefold()
            for term in ("notimplementederror", "unfinished", "print statement", "print(")
        ):
            raise ValueError(
                "The learner task must return a result, not preserve the placeholder or print it"
            )
        if any(
            "```" in text or "~~~" in text for text in (self.explanation, self.result_description)
        ):
            raise ValueError(
                "Describe the task in prose, without code blocks or a completed solution"
            )
        return self

    def code(self) -> str:
        return (
            "# Illustrative data, not your dataset.\n"
            f"sample_data = {sample_value(self.example_json)!r}\n\n"
            "def practice(data):\n"
            "    # Implement the task described above.\n"
            '    raise NotImplementedError("Write your implementation here.")\n\n'
            "# After completing practice, uncomment this to try your result:\n"
            "# print(practice(sample_data))"
        )

    def render(self) -> str:
        value = sample_value(self.example_json)
        access = (
            " Available entries: " + ", ".join(f"data[{key!r}]" for key in value) + "."
            if isinstance(value, dict) and value
            else " Use the argument data as your input value."
        )
        return (
            f"{self.explanation}\n\n"
            "Your task: Replace the placeholder inside `practice(data)` and return "
            f"the following result: {self.result_description}\n\n"
            f"Input: the function receives sample_data as data.{access} "
            "Use this argument, not similarly named variables from earlier code or the tutor description. "
            "Names in the description refer to entries in this input, not separate variables.\n\n"
            f"```python\n{self.code()}\n```\n\n"
            "The app supplied this unfinished template using illustrative data and Python built-ins. "
            "It has not been run, and the tutor's task and explanation have not been independently verified. "
            "Inside practice, data contains sample_data. Replace the placeholder with an implementation "
            "that returns your result, then uncomment the final line to try it."
        )
