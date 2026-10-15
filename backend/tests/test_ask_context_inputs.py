"""Read-only resolver ownership, branch, bounds and explicit source checks."""

from uuid import uuid4

import pytest
from sqlalchemy import func, select

from app.core.errors import AppError
from app.db import answers
from app.db.models import LearnerProfile, ModelCall, TutorAnswer
from app.orchestrator.ask_context_inputs import resolve
from app.schemas.ask import ConversationBrief
from tests.test_ask_sources import setup


async def turn(db, learner, parent=None, text="An unverified explanation", area=None):
    return await answers.save_completed(
        db,
        learner_id=learner.id,
        session_id=None,
        turn_id=str(uuid4()),
        surface="ask",
        request={"question": "Explain this example"},
        text=text,
        metadata={"parent_answer_id": parent, "area_id": area},
    )


async def test_only_selected_branch_and_three_recent_turns(db, learner):
    rows = []
    for _ in range(5):
        rows.append(await turn(db, learner, rows[-1].id if rows else None))
    sibling = await turn(db, learner, rows[0].id, text="Sibling must not leak")
    await db.commit()
    draft = ConversationBrief(task="Unsaved current task")
    result = await resolve(db, learner.id, rows[-1].id, None, draft)
    assert result.history_turns == 3 and result.older_history_omitted
    assert {i.record_id for i in result.inputs.values()} == {r.id for r in rows[-3:]}
    assert sibling.id not in {i.record_id for i in result.inputs.values()}
    assert result.brief_json == draft.model_dump_json()
    changed = await resolve(db, learner.id, rows[-1].id, None, ConversationBrief(task="Different"))
    assert changed.brief_hash != result.brief_hash
    assert await db.scalar(select(func.count()).select_from(ModelCall)) == 0


async def test_foreign_owner_and_surface_rejected(db, learner):
    other = LearnerProfile(display_name="Other")
    db.add(other)
    await db.flush()
    row = await turn(db, other)
    with pytest.raises(AppError):
        await resolve(db, learner.id, row.id, None, ConversationBrief())
    own = await turn(db, learner)
    own.surface = "playground"
    await db.commit()
    with pytest.raises(AppError):
        await resolve(db, learner.id, own.id, None, ConversationBrief())


@pytest.mark.parametrize("bad_parent", [[], {}, "", "missing"])
async def test_malformed_or_missing_ancestor_rejected(db, learner, bad_parent):
    row = await turn(db, learner)
    row.metadata_json = {"parent_answer_id": bad_parent, "area_id": None}
    await db.commit()
    with pytest.raises(AppError):
        await resolve(db, learner.id, row.id, None, ConversationBrief())


async def test_cycles_area_mismatch_and_oversize_rejected(db, learner):
    row = await turn(db, learner)
    row.metadata_json = {"parent_answer_id": row.id, "area_id": None}
    await db.commit()
    with pytest.raises(AppError):
        await resolve(db, learner.id, row.id, None, ConversationBrief())
    row.metadata_json = {"area_id": "different"}
    await db.commit()
    with pytest.raises(AppError):
        await resolve(db, learner.id, row.id, None, ConversationBrief())
    row.metadata_json = {"area_id": None}
    row.text = "x" * 24001
    await db.commit()
    with pytest.raises(AppError):
        await resolve(db, learner.id, row.id, None, ConversationBrief())


async def test_only_explicit_current_sources(db, learner, fake_local):
    _, body, chunk, provenance = await setup(db, learner, fake_local)
    row = await turn(db, learner)
    await db.commit()
    without = await resolve(db, learner.id, row.id, None, ConversationBrief())
    assert "S1" not in without.inputs
    selected = await resolve(db, learner.id, row.id, None, ConversationBrief(), body.sources)
    assert selected.inputs["S1"].record_id == chunk.id
    assert selected.inputs["S1"].origin == "selected_source"
    chunk.text = "changed"
    await db.commit()
    with pytest.raises(AppError):
        await resolve(db, learner.id, row.id, None, ConversationBrief(), body.sources)
    assert not fake_local.calls
    assert await db.scalar(select(func.count()).select_from(TutorAnswer)) == 1


@pytest.mark.parametrize("parent", ["", "   ", "x" * 129])
async def test_parent_must_identify_a_saved_turn(db, learner, parent):
    with pytest.raises(AppError):
        await resolve(db, learner.id, parent, None, ConversationBrief())


async def test_mutated_brief_is_revalidated_before_resolution(db, learner):
    from pydantic import ValidationError

    brief = ConversationBrief()
    brief.task = "x" * 501
    with pytest.raises(ValidationError):
        await resolve(db, learner.id, "parent", None, brief)


async def test_opening_question_retained_without_old_answer(db, learner):
    root = await turn(db, learner, text="Old answer must not be included")
    parent = root
    for _ in range(4):
        parent = await turn(db, learner, parent.id)
        parent.metadata_json = {**parent.metadata_json, "conversation_id": root.turn_id}
    await db.commit()
    result = await resolve(db, learner.id, parent.id, None, ConversationBrief())
    assert result.inputs["opening:question"].record_id == root.id
    assert result.inputs["opening:question"].origin == "learner_statement"
    assert not result.opening_unavailable
    assert all(i.text != root.text for i in result.inputs.values())
    assert result.older_history_omitted
    root.request_json = {"question": "Changed opening"}
    await db.commit()
    updated = await resolve(db, learner.id, parent.id, None, ConversationBrief())
    assert (
        updated.inputs["opening:question"].version_hash
        != result.inputs["opening:question"].version_hash
    )


@pytest.mark.parametrize("invalid", ["foreign", "area", "not_root", "blank", "oversized"])
async def test_invalid_opening_is_disclosed_without_including_text(db, learner, invalid):
    root = await turn(db, learner)
    parent = root
    for _ in range(4):
        parent = await turn(db, learner, parent.id)
        parent.metadata_json = {**parent.metadata_json, "conversation_id": root.turn_id}
    if invalid == "foreign":
        other = LearnerProfile(display_name="Other")
        db.add(other)
        await db.flush()
        root.learner_id = other.id
    elif invalid == "area":
        root.metadata_json = {**root.metadata_json, "area_id": "elsewhere"}
    elif invalid == "not_root":
        root.metadata_json = {**root.metadata_json, "parent_answer_id": "other"}
    else:
        root.request_json = {"question": " " if invalid == "blank" else "x" * 2001}
    await db.commit()
    result = await resolve(db, learner.id, parent.id, None, ConversationBrief())
    assert result.opening_unavailable
    assert "opening:question" not in result.inputs
