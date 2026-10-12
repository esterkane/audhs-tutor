import hashlib
import json

import pytest
from pydantic import ValidationError

from app.db.models import Chunk, LearningObject
from app.kernel.visual_binding import validate_binding
from app.schemas.visual_binding import VisualBinding


def fixture():
    obj = LearningObject(
        id="object",
        version=2,
        skill_id="skill",
        goal="Fit on training data",
        success_criteria_json=["Explain leakage", "Explain leakage"],
        sources_json=["chunk"],
    )
    chunk = Chunk(id="chunk", document_version_id="version", text="Training only.")
    payload = dict(
        schema_version="visual-binding.v1",
        object_id="object",
        object_version=2,
        skill_id="skill",
        goal=obj.goal,
        criteria=[dict(index=1, text="Explain leakage")],
        sources=[
            dict(
                chunk_id="chunk",
                document_version_id="version",
                text_sha256=hashlib.sha256(chunk.text.encode()).hexdigest(),
            )
        ],
    )
    return obj, chunk, payload


def test_exact_binding_accepts_json_and_does_not_change_records():
    obj, chunk, payload = fixture()
    binding = VisualBinding.model_validate_json(json.dumps(payload))
    validate_binding(binding, obj, {chunk.id: chunk})
    assert obj.version == 2 and obj.sources_json == ["chunk"]
    assert binding.criteria[0].index == 1  # repeated text does not erase identity


@pytest.mark.parametrize(
    "field,value",
    [
        ("object_id", "other"),
        ("object_version", 3),
        ("skill_id", "other"),
        ("goal", "Different objective"),
        ("criteria", [dict(index=2, text="Explain leakage")]),
        ("criteria", [dict(index=0, text="Changed criterion")]),
    ],
)
def test_rejects_stale_or_wrong_object(field, value):
    obj, chunk, payload = fixture()
    payload[field] = value
    binding = VisualBinding.model_validate_json(json.dumps(payload))
    with pytest.raises(ValueError):
        validate_binding(binding, obj, {chunk.id: chunk})


@pytest.mark.parametrize("change", ["unrelated", "missing", "version", "text", "wrong_record"])
def test_rejects_unverified_sources(change):
    obj, chunk, payload = fixture()
    binding = VisualBinding.model_validate_json(json.dumps(payload))
    chunks = {"chunk": chunk}
    if change == "unrelated":
        obj.sources_json = []
    elif change == "missing":
        chunks = {}
    elif change == "version":
        chunk.document_version_id = "other"
    elif change == "text":
        chunk.text = "Changed."
    else:
        chunk.id = "other"
    with pytest.raises(ValueError):
        validate_binding(binding, obj, chunks)


@pytest.mark.parametrize("change", ["duplicate", "empty", "extra", "coercion", "oversized"])
def test_strict_bounded_envelope(change):
    _, _, payload = fixture()
    if change == "duplicate":
        payload["criteria"] *= 2
    elif change == "empty":
        payload["sources"] = []
    elif change == "extra":
        payload["script"] = "alert(1)"
    elif change == "coercion":
        payload["object_version"] = "2"
    else:
        payload["goal"] = "x" * 4001
    with pytest.raises(ValidationError):
        VisualBinding.model_validate_json(json.dumps(payload))
