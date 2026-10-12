import json

import pytest
from pydantic import ValidationError

from app.schemas.visual_relationship import MAX_RELATIONSHIP_BYTES, parse_relationship


def payload():
    return {
        "schema_version": "visual.v1",
        "kind": "relationship",
        "binding": {
            "schema_version": "visual-binding.v1",
            "object_id": "lesson",
            "object_version": 1,
            "skill_id": "skill",
            "goal": "Explain feedback",
            "criteria": [{"index": 0, "text": "Trace a feedback loop"}],
            "sources": [
                {"chunk_id": "chunk", "document_version_id": "version", "text_sha256": "a" * 64}
            ],
        },
        "title": "Feedback",
        "text_equivalent": "A affects B; B affects A. C is separate.",
        "directed": True,
        "nodes": [
            {"id": x, "label": x, "explanation": f"Concept {x}", "source_chunk_ids": ["chunk"]}
            for x in ["A", "B", "C"]
        ],
        "edges": [
            {"id": "ab", "source": "A", "target": "B", "label": "affects"},
            {"id": "ba", "source": "B", "target": "A", "label": "affects"},
        ],
    }


def parse(data):
    return parse_relationship(json.dumps(data).encode())


def test_preserves_cycles_and_disconnected_concepts():
    visual = parse(payload())
    assert [node.id for node in visual.nodes] == ["A", "B", "C"]
    assert [(e.source, e.target) for e in visual.edges] == [("A", "B"), ("B", "A")]
    assert parse_relationship(visual.model_dump_json().encode()) == visual


def test_isolated_single_node_and_undirected_relationship_are_valid():
    data = payload()
    data["nodes"] = data["nodes"][:1]
    data["edges"] = []
    data["directed"] = False
    assert not parse(data).directed


@pytest.mark.parametrize(
    "change",
    [
        "duplicate_node",
        "duplicate_edge",
        "missing_endpoint",
        "foreign_source",
        "duplicate_source",
        "nodes_limit",
        "edges_limit",
        "empty_text",
        "wrong_kind",
        "script",
        "node_html",
        "edge_callback",
        "url_loader",
        "position",
        "coercion",
    ],
)
def test_rejects_invalid_or_executable_shapes(change):
    data = payload()
    if change == "duplicate_node":
        data["nodes"][1]["id"] = "A"
    elif change == "duplicate_edge":
        data["edges"][1]["id"] = "ab"
    elif change == "missing_endpoint":
        data["edges"][0]["target"] = "missing"
    elif change == "foreign_source":
        data["nodes"][0]["source_chunk_ids"] = ["unrelated"]
    elif change == "duplicate_source":
        data["nodes"][0]["source_chunk_ids"] = ["chunk", "chunk"]
    elif change == "nodes_limit":
        data["nodes"] *= 22
    elif change == "edges_limit":
        data["edges"] *= 65
    elif change == "empty_text":
        data["text_equivalent"] = ""
    elif change == "wrong_kind":
        data["kind"] = "spatial"
    elif change == "script":
        data["script"] = "fetch('https://example.com')"
    elif change == "node_html":
        data["nodes"][0]["html"] = "<img src=x>"
    elif change == "edge_callback":
        data["edges"][0]["onClick"] = "run()"
    elif change == "url_loader":
        data["data_url"] = "https://example.com/graph"
    elif change == "position":
        data["nodes"][0]["position"] = {"x": float("nan"), "y": 0}
    else:
        data["directed"] = "true"
    with pytest.raises(ValidationError):
        parse(data)


@pytest.mark.parametrize("raw", [b"[]", b"null", b"{", b'"text"', b"\xff"])
def test_malformed_json_is_a_validation_failure(raw):
    with pytest.raises(ValidationError):
        parse_relationship(raw)


def test_bytes_cap_precedes_json_parsing():
    with pytest.raises(ValueError, match="byte limit"):
        parse_relationship(b" " * (MAX_RELATIONSHIP_BYTES + 1))
