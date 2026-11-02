import copy

import pytest

from app.integrations.supabase_citation_repair import CitationRepair, RepairDeclined, apply, prepare
from app.integrations.supabase_project import project_module


def fixture():
    project_module()
    from backend.tutor.guard import GuardContext

    turn = project_module().TutorTurn(
        mode="lesson",
        language="en",
        persona_on=False,
        text=(
            "PostgreSQL 17 supports this mechanism.  \n\n"
            "All qualifications remain unchanged.\n\nPostgreSQL 17 is the stated version."
        ),
        speech="Original speech.",
        next_question="Which premise matters?",
        citations=[
            {
                "n": 1,
                "url": "https://www.postgresql.org/docs/17/",
                "title": "Documentation",
                "tier": 1,
            }
        ],
    )
    return turn, GuardContext(sources={"https://www.postgresql.org/docs/17": 1})


def test_only_markers_inserted_and_original_metadata_untouched():
    turn, context = fixture()
    original = copy.deepcopy(turn.model_dump())
    placement = prepare(turn, context)
    assert placement is not None and len(placement.targets) == 2
    text, metadata = apply(
        turn,
        context,
        placement,
        CitationRepair(
            patches=[{"target": 0, "sources": [1]}, {"target": 1, "sources": [1]}],
            unsupported_targets=[],
        ),
    )
    assert text.replace(" [1]", "") == turn.text
    assert metadata == turn.model_dump(mode="json", exclude={"text", "guard_flags"})
    assert turn.model_dump() == original


@pytest.mark.parametrize(
    "patches,unsupported",
    [
        ([{"target": 0, "sources": [2]}, {"target": 1, "sources": [1]}], []),
        ([{"target": 0, "sources": [1]}], []),
        ([{"target": 0, "sources": [1]}, {"target": 0, "sources": [1]}], []),
        ([{"target": 0, "sources": [1, 1]}, {"target": 1, "sources": [1]}], []),
        ([], [0, 1]),
    ],
)
def test_invalid_or_unsupported_placement_requires_full_repair(patches, unsupported):
    turn, context = fixture()
    with pytest.raises(RepairDeclined):
        apply(
            turn,
            context,
            prepare(turn, context),
            CitationRepair(patches=patches, unsupported_targets=unsupported),
        )


@pytest.mark.parametrize("change", ["prose", "sources"])
def test_stale_context_is_rejected(change):
    turn, context = fixture()
    placement = prepare(turn, context)
    if change == "prose":
        turn = turn.model_copy(update={"text": turn.text + "Changed"})
    else:
        context.sources.clear()
    with pytest.raises(RepairDeclined):
        apply(turn, context, placement, CitationRepair(patches=[], unsupported_targets=[]))


@pytest.mark.parametrize(
    "text",
    [
        "- PostgreSQL 17 needs a source.",
        "## PostgreSQL 17",
        "PostgreSQL 17.\n```sql\nselect 1;\n```",
    ],
)
def test_complex_markdown_retains_full_repair(text):
    turn, context = fixture()
    assert prepare(turn.model_copy(update={"text": text}), context) is None


def test_other_blocking_findings_never_use_placement_only():
    turn, context = fixture()
    assert prepare(turn.model_copy(update={"speech": "https://example.invalid"}), context) is None


@pytest.mark.parametrize("source", [True, 1.0, "1"])
def test_source_numbers_must_be_strict_integers(source):
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        CitationRepair(patches=[{"target": 0, "sources": [source]}], unsupported_targets=[])


def test_changed_citation_identity_is_not_reused():
    turn, context = fixture()
    placement = prepare(turn, context)
    other = "https://www.postgresql.org/docs/17/other.html"
    turn = turn.model_copy(
        update={"citations": [turn.citations[0].model_copy(update={"url": other})]}
    )
    context.sources[other] = 1
    with pytest.raises(RepairDeclined):
        apply(turn, context, placement, CitationRepair(patches=[], unsupported_targets=[]))


@pytest.mark.parametrize("decline", [False, True])
async def test_hosted_placement_and_bounded_full_fallback(monkeypatch, decline):
    from types import SimpleNamespace
    from unittest.mock import AsyncMock

    from app.integrations import supabase_bridge as bridge
    from app.models_ai.provider import ModelSpec
    from tests.test_supabase_local_bridge import setup_bridge

    turn, context = fixture()
    repair = CitationRepair(
        patches=[] if decline else [{"target": 0, "sources": [1]}, {"target": 1, "sources": [1]}],
        unsupported_targets=[0, 1] if decline else [],
    )
    client, call, db, _ = setup_bridge(monkeypatch, decision=repair)
    monkeypatch.setattr(
        bridge,
        "choose_project_study",
        AsyncMock(
            return_value=SimpleNamespace(
                complete=call, spec=ModelSpec(provider="openai", model="test", registry_id="test")
            )
        ),
    )
    schemas = []

    def result(parsed):
        return SimpleNamespace(
            result=SimpleNamespace(parsed=parsed, tokens_in=10, tokens_out=10), model_call_id="test"
        )

    async def complete(*args, **kwargs):
        schemas.append(kwargs["response_model"])
        if len(schemas) == 1:
            return result(repair)
        assert "HOST CITATION-ONLY REPAIR" not in args[1][-1].content
        return result(bridge.LocalDecision(text="Full repair chosen."))

    call.side_effect = complete
    history = [{"role": "user", "content": "Original complete question"}]
    before = copy.deepcopy(history)
    async with client.messages.stream(
        system=[], messages=history, tools=[], _audhs_citation_repair=(turn, context)
    ) as stream:
        final = await stream.get_final_message()
    assert history == before
    assert schemas[0] is CitationRepair
    assert len(schemas) == (2 if decline else 1)
    assert db.commit.await_count >= len(schemas)
    if decline:
        assert schemas[1] is not CitationRepair
        assert final.content[0].text == "Full repair chosen."
    else:
        assert "All qualifications remain unchanged." in final.content[0].text
        assert "PostgreSQL 17 is the stated version. [1]" in final.content[0].text


async def test_local_generation_does_not_enable_hosted_repair(monkeypatch):
    from tests.test_supabase_local_bridge import setup_bridge

    turn, context = fixture()
    client, call, _, _ = setup_bridge(monkeypatch)
    async with client.messages.stream(
        system=[], messages=[], tools=[], _audhs_citation_repair=(turn, context)
    ):
        pass
    assert call.call_args.kwargs["response_model"] is not CitationRepair
    assert call.call_args.kwargs["metadata"]["citation_only_repair"] is False
