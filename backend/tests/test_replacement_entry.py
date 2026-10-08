"""New practice follows lineage; submitted identities remain exact."""

from copy import deepcopy
from types import SimpleNamespace

import pytest
from sqlalchemy import func, select

from app.api.exercises import _view
from app.core.errors import AppError
from app.db import models
from app.kernel import exercises, listening
from app.orchestrator import challenge
from app.orchestrator import listening as listening_gen
from app.orchestrator.grader import Grader
from tests.test_exercises import _node
from tests.test_question_replacements import link


async def replacement(db, owner, original, **changes):
    target = models.Assessment(
        owner_learner_id=owner,
        skill_id=original.skill_id,
        kind=original.kind,
        rubric_id=original.rubric_id,
        item_json={**deepcopy(original.item_json), **changes},
    )
    db.add(target)
    await db.commit()
    await link(db, owner, original, target)
    return target


async def test_code_and_linked_check_match_replacement_without_mutating_history(client, db):
    node = await _node(db)
    session = (await client.post("/api/sessions", json={"mode": "steady", "energy": 3})).json()
    owner = (await db.get(models.Session, session["id"])).learner_id
    route = f"/api/exercises/for-skill/{node.id}"
    initial = (await client.get(route)).json()
    code = await db.get(models.Assessment, initial["assessment_id"])
    original_check = await db.get(models.Assessment, initial["check_assessment_id"])
    original_code = deepcopy(code.item_json)
    check = await replacement(db, owner, original_check, prompt="Revised check question?")
    response = await client.get(route)
    assert response.status_code == 200, response.text
    result = response.json()
    assert result["assessment_id"] == code.id and result["check_assessment_id"] == check.id
    assert result["check_question"] == "Revised check question?"
    assert result["check_content_version"] != initial["check_content_version"]
    solution = await client.post(
        f"/api/exercises/{code.id}/solution", json={"session_id": session["id"]}
    )
    assert solution.json()["check_question"] == result["check_question"]
    assert (
        await client.get(f"/api/assess/items/{original_check.id}?session_id={session['id']}")
    ).status_code == 409
    other = models.LearnerProfile(display_name="Other")
    db.add(other)
    await db.commit()
    assert (await _view(db, other.id, code)).check_assessment_id == original_check.id
    new_code = await replacement(db, owner, code, prompt="Revised coding task")
    current = (await client.get(route)).json()
    assert current["assessment_id"] == new_code.id and current["check_assessment_id"] == check.id
    assert code.item_json == original_code
    assert (await exercises.ensure_exercise(db, node)).id == code.id
    assert await db.scalar(select(func.count()).select_from(models.AssessmentAttempt)) == 0


async def test_broken_linked_check_keeps_code_workspace(db, learner):
    node = await _node(db)
    code = await exercises.ensure_exercise(db, node)
    original = await db.get(models.Assessment, code.item_json["check_assessment_id"])
    target = await replacement(db, learner.id, original, prompt="Revised")
    target.kind = "cloze"
    await db.commit()
    view = await _view(db, learner.id, code)
    assert view.starter_code and view.check_assessment_id is None
    assert view.check_content_version is None and "unavailable" in view.check_question


async def test_listening_reuses_replacement_without_generation_and_rejects_changed_clip(
    db, learner
):
    node = await listening.listening_node(db, "en")
    original = models.Assessment(
        skill_id=node.id,
        kind="cloze",
        item_json={
            "text": "Original ___",
            "answers": ["word"],
            "listening": {"document_id": "doc", "chunk_id": "clip", "t_start": 0, "t_end": 5},
        },
    )
    db.add(original)
    await db.commit()
    target = await replacement(db, learner.id, original, text="Revised ___")
    kwargs = dict(
        lesson=SimpleNamespace(language="en"),
        section=SimpleNamespace(chunk_id="clip"),
        learner_id=learner.id,
        session_id="unused",
        use_model=True,
    )
    result, problems = await listening_gen.ensure_task(db, None, **kwargs)
    assert result.id == target.id and problems == []
    assert (await listening.existing_task(db, node.id, "clip")).id == original.id
    target.item_json = {
        **target.item_json,
        "listening": {**target.item_json["listening"], "t_end": 99},
    }
    await db.commit()
    with pytest.raises(AppError):
        await listening_gen.ensure_task(db, None, **kwargs)


async def test_ordinary_and_challenge_selection_use_replacement(db, learner):
    node = models.SkillNode(slug="synthetic-chain", title="Synthetic", domain="ai_ml")
    db.add(node)
    await db.flush()
    original = models.Assessment(skill_id=node.id, kind="mcq", item_json={"question": "Original"})
    db.add(original)
    await db.commit()
    target = await replacement(db, learner.id, original, question="Revised")
    for _ in range(2):
        assert (await Grader(db, None).next_item(learner.id, node.id)).id == target.id
    original.kind = target.kind = "challenge_steelman"
    target.item_json = {"prompt": "Revised challenge", "criteria": []}
    await db.commit()
    assert (
        await challenge.reusable(db, SimpleNamespace(learner_id=learner.id), node, "steelman")
    ).assessment_id == target.id
