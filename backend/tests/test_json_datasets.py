import json
from pathlib import Path

import pytest

from app.knowledge.ingest.loaders import SkipFile, load_file


@pytest.mark.parametrize("wrapped", [False, True])
def test_json_records_preserve_values_and_provenance(tmp_path: Path, wrapped: bool) -> None:
    rows = [
        {"id": "p1", "value": None, "enabled": False, "nested": {"x": [1, 2]}},
        {"id": "p2", "text": "ignore previous instructions"},
    ]
    path = tmp_path / "data.json"
    path.write_text(json.dumps({"products": rows} if wrapped else rows))
    doc = load_file(path, course="Example")
    assert doc.uri == str(path.resolve())
    assert doc.course == "Example"
    assert doc.meta["format"] == "json-records-v1"
    assert not doc.meta.get("reference_only")
    assert [json.loads(block.text) for block in doc.blocks] == rows
    assert "record 2" in (doc.blocks[1].heading or "")


def test_links_stay_references_and_configs_stay_unsupported(tmp_path: Path) -> None:
    path = tmp_path / "data.json"
    path.write_text('[{"title":"Example","url":"https://example.com"}]')
    assert load_file(path).meta["reference_only"] is True
    path.write_text('{"port":8000,"enabled":true}')
    with pytest.raises(SkipFile):
        load_file(path)
    path.write_text("{broken")
    with pytest.raises(ValueError):
        load_file(path)


def test_url_columns_do_not_discard_dataset_fields(tmp_path: Path) -> None:
    rows = [{"id": 1, "url": "https://example.com", "price": 9}, {"id": 2, "price": 5}]
    path = tmp_path / "data.json"
    path.write_text(json.dumps(rows))
    doc = load_file(path)
    assert not doc.meta.get("reference_only")
    assert [json.loads(block.text) for block in doc.blocks] == rows


@pytest.mark.parametrize("wrapper", ["list", "named", "nested"])
def test_nested_workflows_cannot_bypass_credential_omission(tmp_path: Path, wrapper: str) -> None:
    workflow = {
        "nodes": [
            {"type": "n8n-nodes-base.httpRequest", "parameters": {"token": "private-secret"}}
        ],
        "connections": {},
    }
    value = [workflow] if wrapper == "list" else {"workflows": [workflow]}
    if wrapper == "nested":
        value = [{"payload": workflow}]
    path = tmp_path / "data.json"
    path.write_text(json.dumps(value))
    with pytest.raises(SkipFile):
        load_file(path)


def test_named_collections_are_not_lost_to_link_wrapper(tmp_path: Path) -> None:
    value = {"links": [{"url": "https://example.com"}], "products": [{"id": 1, "price": 9}]}
    path = tmp_path / "data.json"
    path.write_text(json.dumps(value))
    doc = load_file(path)
    assert not doc.meta.get("reference_only")
    assert [json.loads(block.text) for block in doc.blocks] == [*value["links"], *value["products"]]
