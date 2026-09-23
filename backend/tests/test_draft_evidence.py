"""Draft objectives must see and retain the passages selected as their evidence."""

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.kernel import curriculum
from app.orchestrator import drafting


def material() -> curriculum.SectionMaterial:
    chunks = [
        {"id": f"setup{i}", "text": "header\n```python\nimport torch\n```", "ordinal": i}
        for i in range(8)
    ]
    chunks += [
        {
            "id": "later-a",
            "text": "header\nFIRST_EVIDENCE " + "attention explanation " * 200,
            "ordinal": 8,
        },
        {
            "id": "later-b",
            "text": "header\nSECOND_EVIDENCE " + "position explanation " * 150,
            "ordinal": 9,
        },
    ]
    return curriculum.SectionMaterial(
        course="Evidence course",
        section="Attention",
        lectures=[
            {"lecture": "Attention", "title": "Attention", "document_id": "doc", "chunks": chunks}
        ],
    )


def test_each_selected_passage_survives_the_excerpt_budget() -> None:
    text = drafting._excerpts(material())
    assert "FIRST_EVIDENCE" in text
    assert "SECOND_EVIDENCE" in text
    assert len(text) < drafting.MAX_EXCERPT_CHARS + 300
    assert "import torch" not in text


async def test_model_object_retains_the_evidence_used_for_its_goal(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    mat = material()
    monkeypatch.setattr(curriculum, "section_material", AsyncMock(return_value=mat))
    slug = curriculum.lecture_slugs(mat)[0]
    result = drafting.DraftSuggestions(
        lessons=[
            drafting.LessonSuggestion(
                slug=slug,
                goal="Explain attention and position.",
                success_criteria=["Explain the role of position."],
            )
        ]
    )
    gateway = SimpleNamespace(
        complete=AsyncMock(
            return_value=SimpleNamespace(
                model_call_id="call",
                result=SimpleNamespace(parsed=result),
            )
        )
    )
    payload, _, failed = await drafting.draft_with_model(
        None,
        gateway,
        "learner",
        course=mat.course,
        section=mat.section,
    )
    assert not failed
    obj = payload["learning_objects"][0]
    assert {"later-a", "later-b"}.issubset(obj["sources"])
    assert len(obj["sources"]) <= curriculum.MAX_SOURCES_PER_OBJECT
    assert set(obj["sources"]) <= {c["id"] for c in mat.lectures[0]["chunks"]}


async def test_model_failure_preserves_deterministic_evidence(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    mat = material()
    monkeypatch.setattr(curriculum, "section_material", AsyncMock(return_value=mat))
    gateway = SimpleNamespace(complete=AsyncMock(side_effect=drafting.NoModelReady("no route")))
    payload, call_id, failed = await drafting.draft_with_model(
        None,
        gateway,
        "learner",
        course=mat.course,
        section=mat.section,
    )
    assert call_id is None and failed == ["Attention"]
    assert payload["learning_objects"] == curriculum.propose_payload(mat)["learning_objects"]
