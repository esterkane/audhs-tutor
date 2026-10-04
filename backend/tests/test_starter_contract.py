import ast
import json
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.db.models import TutorAnswer
from app.models_ai.registry import seed_defaults
from app.schemas.starter import StarterPlan


def plan(**updates):
    return StarterPlan.model_validate(
        {
            "explanation": "Practice a small calculation.",
            "result_description": "The sum of the input values in data.",
            "example_json": "[1, 2]",
            **updates,
        }
    )


def test_template_contains_real_placeholder_and_no_model_code():
    payload = "\nimport os\nos.system('echo not-executed')\n"
    value = plan(example_json=json.dumps({"text": payload, "value": None}))
    tree = ast.parse(value.code())
    assert ast.literal_eval(tree.body[0].value) == {"text": payload, "value": None}
    function = tree.body[1]
    assert isinstance(function, ast.FunctionDef)
    assert function.name == "practice"
    assert len(function.body) == 1 and isinstance(function.body[0], ast.Raise)
    assert not any(isinstance(node, (ast.Import, ast.ImportFrom)) for node in ast.walk(tree))
    assert len(tree.body) == 2  # No invocation or solution after the placeholder.


@pytest.mark.parametrize(
    "text",
    [
        "NaN",
        "1e999",
        "[Infinity]",
        "[" * 9 + "0" + "]" * 9,
        json.dumps(list(range(201))),
        "not json",
    ],
)
def test_invalid_or_unbounded_example_rejected(text):
    with pytest.raises(ValidationError):
        plan(example_json=text)


def test_arbitrary_code_and_fenced_prose_rejected():
    with pytest.raises(ValidationError):
        plan(code="import numpy")
    with pytest.raises(ValidationError):
        plan(explanation="```python\nprint(1)\n```")


async def test_starter_response_is_assembled_saved_and_replayed(client, db, fake_local):
    await seed_defaults(db, installed_ollama_tags={"llama3.1:8b"})
    session = (await client.post("/api/sessions", json={"mode": "steady", "energy": 3})).json()
    fake_local.structured = plan().model_dump()
    fake_local.fail_structured_times = 1  # Existing bounded gateway repair path.
    body = {
        "session_id": session["id"],
        "exercise": "Learn to add numbers",
        "code": "keep = 1",
        "intent": "starter",
        "question": "Give me a small starter",
    }
    headers = {"Idempotency-Key": str(uuid4())}
    first = await client.post("/api/playground/tutor", json=body, headers=headers)
    assert first.status_code == 200, first.text
    assert "raise NotImplementedError" in first.json()["text"]
    assert "has not been run" in first.json()["text"]
    saved = await db.get(TutorAnswer, first.json()["answer_id"])
    assert saved.metadata_json["starter_contract"] == "starter.scaffold.v1"
    assert saved.request_json["code"] == "keep = 1"
    calls = len(fake_local.calls)
    assert calls == 2
    replay = await client.post("/api/playground/tutor", json=body, headers=headers)
    assert replay.json() == first.json()
    assert len(fake_local.calls) == calls


@pytest.mark.parametrize(
    "task",
    [
        "Leave the task unfinished.",
        "Raise NotImplementedError for this task.",
        "Use a print statement for the result.",
    ],
)
def test_contradictory_task_directions_are_rejected(task):
    with pytest.raises(ValidationError):
        plan(result_description=task)


def test_render_names_actual_input_keys_and_application_owned_function():
    rendered = plan(example_json='{"a": [1], "b": [2]}').render()
    assert "inside `practice(data)`" in rendered
    assert "data['a'], data['b']" in rendered
    assert "has not been run" in rendered
