import sqlite3

import pytest

from app.core.errors import AppError
from app.db import answer_checks
from app.db.models import LearnerProfile, ModelCall, TutorAnswer
from app.db.portability import export_learner, wipe_learner
from app.orchestrator.answer_check_binding import bind_review, load_bound_review
from app.schemas.answer_checks import AnswerReviewProposal


async def fixture(db, learner):
    answer = TutorAnswer(
        learner_id=learner.id,
        turn_id="turn",
        surface="ask",
        request_json={"question": "Why?"},
        text="A byte has eight bits.",
        metadata_json={},
        fingerprint="test",
    )
    call = ModelCall(
        learner_id=learner.id,
        provider="ollama",
        model="test",
        registry_id="test",
        task="chat",
        outcome="ok",
    )
    db.add_all([answer, call])
    await db.commit()
    proposal = AnswerReviewProposal(
        claims=[
            dict(
                claim_quote=answer.text,
                verdict="insufficient",
                explanation="No passage provided.",
            )
        ]
    )
    from app.orchestrator.answer_check_binding import text_hash

    call.metadata_json = {
        "surface": "ask_check",
        "answer_id": answer.id,
        "answer_hash": text_hash(answer.text),
        "prompt_version": "test.v1",
    }
    await db.commit()
    return dict(
        learner_id=learner.id,
        answer_id=answer.id,
        model_call_id=call.id,
        prompt_version="test.v1",
        receipt_json=bind_review(answer.text, {}, proposal).receipt_json,
    )


async def test_review_is_owned_replayable_and_exported(db, learner, db_path):
    args = await fixture(db, learner)
    row = await answer_checks.save(db, **args)
    await db.commit()
    assert (await answer_checks.save(db, **args)).id == row.id
    other = LearnerProfile(display_name="Other")
    db.add(other)
    await db.commit()
    with pytest.raises(AppError, match="unavailable"):
        await answer_checks.owned(db, other.id, row.id)
    with pytest.raises(AppError, match="unavailable"):
        await answer_checks.save(db, **{**args, "learner_id": other.id})
    with sqlite3.connect(db_path) as conn:
        conn.execute("PRAGMA foreign_keys=ON")
        assert len(export_learner(conn, learner.id)["answer_check"]) == 1
        assert wipe_learner(conn, learner.id)["answer_check"] == 1
        assert export_learner(conn, other.id)["learner_profile"]


async def test_changed_answer_and_conflicting_call_cannot_relabel_review(db, learner):
    args = await fixture(db, learner)
    row = await answer_checks.save(db, **args)
    await db.commit()
    with pytest.raises(AppError, match="does not match"):
        await answer_checks.save(db, **{**args, "prompt_version": "changed.v2"})
    answer = await db.get(TutorAnswer, args["answer_id"])
    answer.text = "Edited"
    await db.commit()
    with pytest.raises(AppError, match="changed"):
        await answer_checks.save(db, **args)
    with pytest.raises(ValueError, match="changed"):
        load_bound_review(row.receipt_json, answer.text, {})


async def test_failed_or_hosted_call_cannot_supply_local_review(db, learner):
    args = await fixture(db, learner)
    call = await db.get(ModelCall, args["model_call_id"])
    call.provider = "openai"
    await db.commit()
    with pytest.raises(AppError, match="completed local"):
        await answer_checks.save(db, **args)
    call.provider, call.ok = "ollama", False
    await db.commit()
    with pytest.raises(AppError, match="completed local"):
        await answer_checks.save(db, **args)


def test_downgrade_refuses_saved_check_loss(tmp_path):
    from alembic import command
    from app.db.migrate import alembic_config, upgrade_to_head
    from tests._rows import fill_all_tables

    path = tmp_path / "checks.db"
    url = f"sqlite:///{path}"
    upgrade_to_head(url)
    fill_all_tables(url)
    with pytest.raises(RuntimeError, match="Cannot discard saved answer checks"):
        command.downgrade(alembic_config(url), "2ef8502090bd")
    with sqlite3.connect(path) as conn:
        assert conn.execute("SELECT count(*) FROM answer_check").fetchone()[0] > 0
