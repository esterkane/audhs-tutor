"""Ungraded prediction → delayed recall, tested with independent requests and synthetic material."""

import asyncio
import sqlite3
from uuid import uuid4

import pytest
from sqlalchemy import select

from alembic import command
from app.api.deps import get_learner
from app.db.migrate import alembic_config
from app.db.models import LearnerProfile, SkillNode
from app.db.portability import export_learner, wipe_learner
from tests.test_knowledge_authoring import complete

BASE = "/api/reading-predictions"


async def accepted(client, db):
    form = complete(explanation_prequestion="What happens when Python joins two strings?")
    resp = await client.post(
        "/api/knowledge-material/drafts", json=form, headers={"Idempotency-Key": str(uuid4())}
    )
    draft = resp.json()
    published = await client.post(
        f"/api/curriculum/drafts/{draft['id']}/publish", json={"expected_version": draft["version"]}
    )
    assert published.status_code == 200, published.text
    skill = await db.scalar(
        select(SkillNode).where(SkillNode.slug == draft["payload"]["skills"][0]["slug"])
    )
    reading = (await client.get(f"/api/knowledge-material/skills/{skill.id}/reading")).json()
    question = reading["prequestions"][0]
    return {
        "draft_id": draft["id"],
        "learning_object_version": reading["learning_object_version"],
        "question_id": question["question_id"],
        "prediction": "They form one string.",
    }, reading


async def test_enroll_due_recall_preserves_frozen_original_and_never_grades(
    client, db, db_path, learner, monkeypatch
):
    enrollment, reading = await accepted(client, db)
    stamp = "2026-11-11T13:00:00.000+00:00"
    monkeypatch.setattr("app.api.reading_predictions.utcnow_iso", lambda: stamp)
    binding = {k: v for k, v in enrollment.items() if k != "prediction"}

    async def get_binding():
        return (await client.get(BASE + "/enrollment", params=binding)).json()

    assert await get_binding() is None and (await client.get(BASE + "/due")).json() is None
    assert (await client.post(BASE, json=enrollment | {"question_id": "a" * 64})).status_code == 409
    assert (
        await client.post(BASE, json=enrollment | {"learning_object_version": 999})
    ).status_code == 409
    responses = await asyncio.gather(*(client.post(BASE, json=enrollment) for _ in range(2)))
    assert all(r.status_code == 200 for r in responses)
    receipt = responses[0].json()
    assert receipt == responses[1].json() == await get_binding()
    assert receipt["due_at"] == "2026-11-12T13:00:00.000+00:00"
    assert (
        await client.post(BASE, json=enrollment | {"prediction": "Competing draft"})
    ).status_code == 409
    recall = BASE + "/" + receipt["id"] + "/recall"
    assert (await client.post(recall, json={"answer": "premature"})).status_code == 409
    assert (await client.get(BASE + "/latest-recall")).json() is None

    # A newer accepted question cannot rebind the enrolled prediction or its passage.
    revision = (
        await client.post(
            f"/api/knowledge-material/drafts/{reading['draft_id']}/revise",
            json={"expected_version": 2},
            headers={"Idempotency-Key": str(uuid4())},
        )
    ).json()
    updated = complete(explanation_prequestion="What does the revised section ask?")
    updated["explanation"] = "Revised accepted sentence."
    edited = await client.put(
        "/api/knowledge-material/drafts/" + revision["id"],
        json=updated | {"expected_version": revision["version"]},
    )
    assert edited.status_code == 200, edited.text
    pub = await client.post(
        "/api/curriculum/drafts/" + revision["id"] + "/publish",
        json={"expected_version": edited.json()["version"]},
    )
    assert pub.status_code == 200, pub.text
    assert (await client.post(BASE, json=enrollment)).json() == receipt

    stamp = "2026-11-12T12:59:59.999+00:00"
    assert (await client.get(BASE + "/due")).json() is None
    stamp = receipt["due_at"]
    due = (await client.get(BASE + "/due")).json()
    assert (
        set(due) == {"id", "title", "question", "due_at"}
        and due["question"] == reading["prequestions"][0]["question"]
    )
    other = LearnerProfile(display_name="Other synthetic learner")
    db.add(other)
    await db.commit()
    overrides = client._transport.app.dependency_overrides
    overrides[get_learner] = lambda: other
    try:
        assert (await client.get(BASE + "/due")).json() is None
        assert (await client.post(recall, json={"answer": "Other learner"})).status_code == 404
        assert await get_binding() is None
    finally:
        overrides.pop(get_learner)
    completed = await client.post(recall, json={"answer": "A single concatenated string."})
    assert completed.status_code == 200
    result = completed.json()
    assert (
        result["passage"] == reading["explanation"]
        and result["prediction"] == enrollment["prediction"]
    )
    assert result["answered_at"] == stamp and result["answer"] == "A single concatenated string."
    assert (await client.get(BASE + "/due")).json() is None
    assert (await client.get(BASE + "/latest-recall")).json() == result
    assert (await client.post(recall, json={"answer": result["answer"]})).json() == result
    assert (await client.post(recall, json={"answer": "Replacement"})).status_code == 409
    await db.commit()
    with sqlite3.connect(db_path) as conn:
        exported = export_learner(conn, learner.id)
        assert len(exported["reading_prediction"]) == 1
        assert exported["reading_prediction"][0]["passage"] == result["passage"]
        for table in [
            "assessment_attempt",
            "competency_evidence",
            "review_log",
            "review_item",
            "memory_state",
            "model_call",
        ]:
            assert exported[table] == []
        assert export_learner(conn, other.id)["reading_prediction"] == []
        assert wipe_learner(conn, learner.id)["reading_prediction"] == 1
        assert conn.execute("SELECT 1 FROM reading_prediction").fetchone() is None


def test_prediction_migration_empty_roundtrip_and_populated_downgrade_guard(tmp_path):
    path = tmp_path / "migration.db"
    cfg = alembic_config("sqlite:///" + str(path))
    command.upgrade(cfg, "head")
    command.downgrade(cfg, "c8e5a1f03972")
    command.upgrade(cfg, "head")
    with sqlite3.connect(path) as conn:
        columns = [
            row[1]
            for row in conn.execute("pragma table_info(reading_prediction)")
            if row[3] or row[5]
        ]
        names = ", ".join(columns)
        conn.execute(
            f"insert into reading_prediction({names}) values ({','.join('?' for _ in columns)})",
            tuple("synthetic" for _ in columns),
        )
    with pytest.raises(RuntimeError, match="populated reading prediction"):
        command.downgrade(cfg, "c8e5a1f03972")
    with sqlite3.connect(path) as conn:
        assert conn.execute("select count(*) from reading_prediction").fetchone() == (1,)


async def test_map_reset_hides_enrollment_and_replay_but_retains_owner_export(
    client, db, db_path, learner, monkeypatch
):
    from app.db.models import LearnerPreference
    from app.kernel.learning_scope import REFERENCE_BEFORE

    request, _ = await accepted(client, db)
    clock = "2030-01-01T13:00:00.000+00:00"
    monkeypatch.setattr("app.api.reading_predictions.utcnow_iso", lambda: clock)
    receipt = (await client.post(BASE, json=request)).json()
    clock = receipt["due_at"]
    assert (await client.get(BASE + "/due")).json()["id"] == receipt["id"]
    db.add(
        LearnerPreference(
            learner_id=learner.id,
            key=REFERENCE_BEFORE,
            value_json="2030-01-01T14:00:00.000+00:00",
            origin="explicit",
        )
    )
    await db.commit()
    params = {k: v for k, v in request.items() if k != "prediction"}
    assert (await client.get(BASE + "/enrollment", params=params)).json() is None
    assert (await client.get(BASE + "/due")).json() is None
    for data in (request, request | {"prediction": "Competing text"}):
        denied = await client.post(BASE, json=data)
        assert (
            denied.status_code == 409 and denied.json()["error"]["code"] == "accuracy_review_only"
        )
    assert (
        await client.post(BASE + "/" + receipt["id"] + "/recall", json={"answer": "Late"})
    ).status_code == 409
    with sqlite3.connect(db_path) as conn:
        rows = export_learner(conn, learner.id)["reading_prediction"]
        assert (
            len(rows) == 1
            and rows[0]["prediction"] == request["prediction"]
            and rows[0]["answer"] is None
        )
