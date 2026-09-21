"""P8 code exercise: catalogue → assessment row (once), public view without solution, hint ladder
(each step logged), explicit full solution (logged) with check question, grading of client check
results (all pass / partial / error / malformed), evidence + FSRS + delayed transfer item through the
ordinary attempt route, exercise excluded from the item rotation, no host execution anywhere."""

import json
from pathlib import Path

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import models
from app.kernel import exercises, skill_graph
from app.kernel.seed import load_seed
from app.orchestrator.grader import Grader

SEED = Path(__file__).resolve().parents[2] / "seeds" / "attention"


async def _node(db: AsyncSession) -> models.SkillNode:
    await load_seed(db, SEED)
    node = await skill_graph.get_node_by_slug(db, "attn-scaled")
    assert node is not None
    return node


def _answer(passed: list[str], failed: dict[str, str] | None = None, **extra: object) -> str:
    results = [{"name": n, "passed": True, "detail": "passed"} for n in passed]
    for n, d in (failed or {}).items():
        results.append({"name": n, "passed": False, "detail": d})
    return json.dumps({"code": "def softmax(x): ...", "results": results, **extra})


def test_grade_code_is_deterministic_and_never_trusts_missing_checks() -> None:
    item = exercises.CATALOGUE["attn-scaled-softmax"]
    item_json = {
        "checks": [{"name": c.name, "criterion": c.criterion, "code": c.code} for c in item.checks],
        "check_question": item.check_question,
    }
    names = [c.name for c in item.checks]
    full, correct = exercises.grade_code(item_json, _answer(names))
    assert correct is True and full.score == 1.0 and "3 checks passed" in full.feedback
    assert full.next_step.startswith("Check question")
    part, correct = exercises.grade_code(
        item_json, _answer(names[:1], {names[1]: "divide the scores by sqrt(d_k)"})
    )
    assert correct is None and part.score == pytest.approx(1 / 3)
    assert "divide the scores by sqrt(d_k)" in part.feedback and "check not run" in " ".join(
        c.evidence for c in part.criterion_results
    )
    err, correct = exercises.grade_code(
        item_json,
        json.dumps({"code": "x = ", "results": [], "error": "SyntaxError: invalid syntax"}),
    )
    assert correct is False and err.score == 0.0 and "SyntaxError" in err.feedback
    assert all(c.evidence.startswith("SyntaxError") for c in err.criterion_results)
    trunc, _ = exercises.grade_code(item_json, _answer(names, truncated=True))
    assert "cut at the limit" in trunc.feedback
    after, _ = exercises.grade_code(item_json, _answer(names, solution_shown=True))
    assert after.confidence == 0.5 and "half weight" in after.feedback
    with pytest.raises(ValueError):
        exercises.grade_code(item_json, "not json")
    with pytest.raises(ValueError):
        exercises.grade_code(item_json, json.dumps({"results": []}))  # no code
    # an error next to "passed" results: the error wins (no check can have run)
    odd, correct = exercises.grade_code(
        item_json,
        json.dumps(
            {"code": "x", "results": [{"name": n, "passed": True} for n in names], "error": "boom"}
        ),
    )
    assert correct is False and odd.score == 0.0
    # duplicate names: the last one counts, nothing doubles
    dup, _ = exercises.grade_code(
        item_json,
        json.dumps(
            {
                "code": "x",
                "results": [
                    {"name": names[0], "passed": False},
                    {"name": names[0], "passed": True},
                ],
            }
        ),
    )
    assert dup.criterion_results[0].passed is True and dup.score == pytest.approx(1 / 3)


async def test_exercise_journey(client: AsyncClient, db: AsyncSession) -> None:
    node = await _node(db)
    r = await client.get(f"/api/exercises/for-skill/{node.id}")
    assert r.status_code == 200, r.text
    ex = r.json()
    assert ex["exercise_id"] == "attn-scaled-softmax" and ex["runtime"] == "pyodide-worker"
    assert "return softmax(scores) @ V" not in json.dumps(ex)  # the solution never travels
    assert "solution" not in ex and "hints" not in ex
    assert ex["hints_available"] == 3 and ex["attempts"] == 0 and ex["packages"] == ["numpy"]
    assert ex["check_assessment_id"] and ex["check_question"].startswith("Check question")
    check = await db.get(models.Assessment, ex["check_assessment_id"])
    assert check is not None and check.kind == "explain_back" and check.rubric_id
    assert ex["policy"]["network"].startswith("best effort") and ex["policy"]["timeout_s"] == 10
    assert len(ex["checks"]) == 3 and all(
        set(c) == {"name", "criterion", "code"} for c in ex["checks"]
    )
    # created once
    r2 = await client.get(f"/api/exercises/for-skill/{node.id}")
    assert r2.json()["assessment_id"] == ex["assessment_id"]
    # a skill without a catalogue entry → 404, never a generated exercise
    other = await skill_graph.get_node_by_slug(db, "softmax")
    assert other is not None
    assert (await client.get(f"/api/exercises/for-skill/{other.id}")).status_code == 404
    # the exercise is not part of the normal item rotation
    s = await client.post("/api/sessions", json={"mode": "steady", "energy": 3, "socratic": False})
    session_id = s.json()["id"]
    nxt = await Grader(db, None).next_item("x", node.id)  # type: ignore[arg-type]
    assert nxt is not None and nxt.kind != "code"
    # hint ladder: one step per explicit request, clamped, each logged
    h1 = (
        await client.post(
            f"/api/exercises/{ex['assessment_id']}/hint",
            json={"session_id": session_id, "level": 1},
        )
    ).json()
    h9 = (
        await client.post(
            f"/api/exercises/{ex['assessment_id']}/hint",
            json={"session_id": session_id, "level": 9},
        )
    ).json()
    assert h1["level"] == 1 and "softmax" in h1["text"].lower()
    assert h9["level"] == 3 and h9["hints_available"] == 3
    # explicit full solution, logged, with a check question
    sol = (
        await client.post(
            f"/api/exercises/{ex['assessment_id']}/solution", json={"session_id": session_id}
        )
    ).json()
    assert "def scaled_attention" in sol["solution"] and sol["check_question"].startswith("Check")
    ev = (await db.execute(select(models.LearningEvent))).scalars().all()
    reps = [e.context_json.get("representation") for e in ev if e.verb == "explained"]
    assert reps == ["code_hint", "code_hint", "full_solution"]
    # submit = the ordinary attempt route; confidence before feedback; hint usage recorded
    names = [c["name"] for c in ex["checks"]]
    r = await client.post(
        "/api/assess/attempt",
        json={
            "session_id": session_id,
            "assessment_id": ex["assessment_id"],
            "answer": _answer(names[:2], {names[2]: "output shape must be (n, d_v)"}),
            "confidence_pre": 3,
            "hint_count": 2,
        },
    )
    assert r.status_code == 200, r.text
    res = r.json()
    assert res["kind"] == "code" and res["dimension"] == "application"
    assert res["score"] == pytest.approx(2 / 3) and res["correct"] is None
    assert res["grader_level"] == "deterministic:client-pyodide"  # one label everywhere
    assert [c["passed"] for c in res["criterion_results"]] == [True, True, False]
    # evidence on the application dimension, a card scheduled ≥ +2 days (delayed transfer item)
    evd = (await db.execute(select(models.CompetencyEvidence))).scalars().all()
    assert len(evd) == 1 and evd[0].dimension == "application" and evd[0].skill_id == node.id
    ms = (await db.execute(select(models.MemoryState))).scalar_one()
    from datetime import UTC, datetime, timedelta

    assert datetime.fromisoformat(ms.due) >= datetime.now(UTC) + timedelta(days=1, hours=23)
    att = (await db.execute(select(models.AssessmentAttempt))).scalar_one()
    assert (
        att.hint_count == 2
        and att.confidence_pre == 3
        and att.grader_route.startswith("deterministic")
    )
    attempted = [e for e in ev if e.verb == "attempted"]
    assert not attempted  # (events list was captured before the attempt)
    ev2 = (await db.execute(select(models.LearningEvent))).scalars().all()
    att_ev = next(e for e in ev2 if e.verb == "attempted")
    assert att_ev.result_json["hint_count"] == 2 and att_ev.result_json["confidence_pre"] == 3
    assert (await client.get(f"/api/exercises/for-skill/{node.id}")).json()["attempts"] == 1
    # the graded event and the attempt row carry the same trust label
    ev3 = (await db.execute(select(models.LearningEvent))).scalars().all()
    graded_ev = next(e for e in ev3 if e.verb == "graded")
    assert graded_ev.context_json["grader_level"] == "deterministic:client-pyodide"
    # as a review card the exercise asks its check question and reveals the criteria, never blank
    from app.orchestrator.grader import view

    a = await db.get(models.Assessment, ex["assessment_id"])
    assert a is not None
    v = view(a)
    assert v.question.startswith("Check question") and v.criteria == ex["success_criteria"]
    # an oversized submission is refused by the schema
    r = await client.post(
        "/api/assess/attempt",
        json={
            "session_id": session_id,
            "assessment_id": ex["assessment_id"],
            "answer": "x" * 20_001,
            "confidence_pre": 3,
        },
    )
    assert r.status_code == 422
    # a malformed submission is refused, not graded
    r = await client.post(
        "/api/assess/attempt",
        json={
            "session_id": session_id,
            "assessment_id": ex["assessment_id"],
            "answer": "print('hi')",
            "confidence_pre": 3,
        },
    )
    assert r.status_code == 400


def test_backend_never_executes_learner_code() -> None:
    """Static guard: nothing in the exercise/grading path calls exec/eval/subprocess/compile."""
    import re

    for rel in ("app/kernel/exercises.py", "app/api/exercises.py"):
        src = (Path(__file__).resolve().parents[1] / rel).read_text()
        assert not re.search(r"\b(exec|eval|compile|subprocess|os\.system|__import__)\s*\(", src), (
            rel
        )
