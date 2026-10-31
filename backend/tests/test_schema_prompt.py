import copy
import json

import instructor
from instructor.v2.core.response import handle_response_model
from pydantic import BaseModel, Field

from app.models_ai.provider import Message
from app.models_ai.schema_prompt import compact_schema_instructions


class Reply(BaseModel):
    title: str = Field(description='Keep quoted text "x" and unicode ü unchanged.')
    values: list[int]


def test_only_generated_schema_whitespace_changes_with_real_sdk():
    pretty = json.dumps(Reply.model_json_schema(), indent=2)
    original = [
        Message(role="system", content="Exact policy " + pretty),
        Message(role="user", content="Exact source and earlier data: " + pretty),
    ]
    prepared, expanded = handle_response_model(
        Reply, mode=instructor.Mode.JSON, messages=[m.model_dump() for m in original]
    )
    before = copy.deepcopy(expanded["messages"])
    assert prepared is not None
    generated_pretty = json.dumps(prepared.model_json_schema(), indent=2, ensure_ascii=False)
    actual = compact_schema_instructions(original, before, prepared)
    compact = json.dumps(prepared.model_json_schema(), separators=(",", ":"), ensure_ascii=False)
    assert actual[0]["content"].startswith(original[0].content)
    assert actual[1:] == before[1:]
    assert (
        actual[0]["content"][len(original[0].content) :].replace(compact, generated_pretty)
        == before[0]["content"][len(original[0].content) :]
    )
    assert before == expanded["messages"]
    assert json.loads(compact) == json.loads(generated_pretty)
    assert len(actual[0]["content"]) < len(before[0]["content"])


def test_unknown_sdk_layout_or_ambiguous_schema_keeps_established_prompt():
    original = [Message(role="system", content="Exact policy")]
    pretty = json.dumps(Reply.model_json_schema(), indent=2)
    for body in [
        "Different policy" + pretty,
        "Exact policy without schema",
        "Exact policy" + pretty + pretty,
    ]:
        expanded = [{"role": "system", "content": body}]
        assert compact_schema_instructions(original, expanded, Reply) is expanded
    assert compact_schema_instructions([], [], Reply) == []


async def test_wire_contract_context_and_output_allowance_are_unchanged(monkeypatch):
    from app.models_ai.ollama import OllamaProvider
    from app.schemas.knowledge_authoring import ResearchDiscussion
    from tests.test_ollama_inference_options import SPEC, intercept

    posts = intercept(monkeypatch)
    provider = OllamaProvider("http://127.0.0.1:11434", context_tokens=16384)
    messages = [
        Message(role="system", content="Preserve exact policy and complete answer."),
        Message(role="user", content="Synthetic source question."),
    ]
    for compact in [False, True]:
        metadata = {"structured_output": "native_schema"}
        if compact:
            metadata["schema_prompt"] = "compact_json.v1"
        result = await provider.complete(
            SPEC, messages, response_model=ResearchDiscussion, metadata=metadata, max_tokens=1600
        )
        assert result.parsed.answer_sentence == "A complete answer."
    assert posts[0]["format"] == posts[1]["format"] == ResearchDiscussion.model_json_schema()
    assert posts[0]["options"] == posts[1]["options"]
    assert posts[1]["options"]["num_predict"] == 1600
    assert posts[1]["options"]["num_ctx"] == 16384
    assert posts[0]["messages"][1:] == posts[1]["messages"][1:]
    pretty = json.dumps(ResearchDiscussion.model_json_schema(), indent=2)
    compact = json.dumps(ResearchDiscussion.model_json_schema(), separators=(",", ":"))
    assert (
        posts[1]["messages"][0]["content"].replace(compact, pretty)
        == posts[0]["messages"][0]["content"]
    )
