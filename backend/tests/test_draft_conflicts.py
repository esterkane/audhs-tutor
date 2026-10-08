"""Stale curriculum editors must not replace a newer reviewed draft."""

import pytest
from sqlalchemy import select

from app.db.models import CurriculumDraft


async def draft_row(db, learner):
    row = CurriculumDraft(
        learner_id=learner.id,
        course="Synthetic material",
        section=None,
        title="Synthetic draft",
        payload_json={},
        validation_json=[],
    )
    db.add(row)
    await db.commit()
    return row


async def test_stale_editor_cannot_overwrite_newer_draft(client, db, learner):
    row = await draft_row(db, learner)
    url = f"/api/curriculum/drafts/{row.id}"
    saved = await client.put(url, json={"expected_version": 1, "payload": {"domain": "language"}})
    assert saved.status_code == 200, saved.text
    assert saved.json()["version"] == 2
    stale = await client.put(url, json={"expected_version": 1, "payload": {"domain": "music"}})
    assert stale.status_code == 409, stale.text
    assert stale.json()["error"]["code"] == "draft_conflict"
    await db.refresh(row)
    assert row.version == 2 and row.payload_json["domain"] == "language"


@pytest.mark.parametrize("action", ["publish", "reject"])
async def test_stale_actions_cannot_activate_or_discard_newer_work(client, db, learner, action):
    row = await draft_row(db, learner)
    url = f"/api/curriculum/drafts/{row.id}"
    assert (
        await client.put(url, json={"expected_version": 1, "payload": {"domain": "language"}})
    ).status_code == 200
    result = await client.post(f"{url}/{action}", json={"expected_version": 1})
    assert result.status_code == 409, result.text
    await db.refresh(row)
    assert row.status == "draft" and row.version == 2


async def test_concurrent_editors_have_one_winner(client, db, learner):
    import asyncio

    row = await draft_row(db, learner)
    url = f"/api/curriculum/drafts/{row.id}"
    results = await asyncio.gather(
        *[
            client.put(url, json={"expected_version": 1, "payload": {"domain": domain}})
            for domain in ("music", "language")
        ]
    )
    assert sorted(r.status_code for r in results) == [200, 409]
    winner = next(r.json() for r in results if r.status_code == 200)
    await db.refresh(row)
    assert row.version == 2 and row.payload_json == winner["payload"]


async def test_version_required_and_ownership_checked(client, db, learner):
    from app.db.models import LearnerProfile

    row = await draft_row(db, learner)
    url = f"/api/curriculum/drafts/{row.id}"
    assert (await client.put(url, json={"payload": {}})).status_code == 422
    assert (await client.post(f"{url}/publish")).status_code == 422
    assert (await client.post(f"{url}/reject")).status_code == 422
    other = LearnerProfile(display_name="Other")
    db.add(other)
    await db.flush()
    row.learner_id = other.id
    await db.commit()
    result = await client.put(url, json={"payload": {}, "expected_version": 1})
    assert result.status_code == 404


async def test_terminal_draft_cannot_be_reactivated(client, db, learner):
    row = await draft_row(db, learner)
    url = f"/api/curriculum/drafts/{row.id}"
    rejected = await client.post(f"{url}/reject", json={"expected_version": 1})
    assert rejected.status_code == 200 and rejected.json()["version"] == 2
    assert (await client.put(url, json={"payload": {}, "expected_version": 1})).status_code == 409
    assert (await client.post(f"{url}/publish", json={"expected_version": 2})).status_code == 400
    await db.refresh(row)
    assert row.status == "rejected" and row.version == 2


async def test_activation_and_edit_serialize_the_reviewed_version(client, db, learner, fake_repo):
    import asyncio

    from sqlalchemy import func

    from app.db.models import SkillNode
    from app.kernel import curriculum
    from tests.test_curriculum import _ingest

    await _ingest(db, fake_repo, "LLM Evaluation")
    section = (await curriculum.sections_of(db, "LLM Evaluation"))[0]["section"]
    row = await curriculum.create_draft(db, learner.id, course="LLM Evaluation", section=section)
    assert not [p for p in row.validation_json if p["level"] == "error"]
    url = f"/api/curriculum/drafts/{row.id}"
    original = row.payload_json
    edit = {**original, "domain": "language"}
    activated, saved = await asyncio.gather(
        client.post(f"{url}/publish", json={"expected_version": 1}),
        client.put(url, json={"expected_version": 1, "payload": edit}),
    )
    assert sorted([activated.status_code, saved.status_code]) == [200, 409], (
        activated.text,
        saved.text,
    )
    await db.refresh(row)
    assert row.version == 2
    if activated.status_code == 200:
        assert row.status == "published" and row.payload_json == original
        assert await db.scalar(select(func.count()).select_from(SkillNode)) == len(
            original["skills"]
        )
    else:
        assert row.status == "draft" and row.payload_json["domain"] == "language"
        assert await db.scalar(select(func.count()).select_from(SkillNode)) == 0
