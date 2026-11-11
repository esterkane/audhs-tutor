"""One synthetic accepted lesson and changing reference; all requests stay offline."""

from uuid import uuid4

from sqlalchemy import select

from app.core.errors import AppError
from app.db.models import KnowledgeArea, SkillNode
from app.knowledge.reference_fetch import FetchedPage
from app.models_ai.fake import FakeProvider
from tests.test_hybrid_authoring import enable
from tests.test_knowledge_authoring import complete


async def test_changed_unreachable_unchanged_and_explicit_revision_acceptance(
    client, db, learner, monkeypatch
):
    area = KnowledgeArea(slug="focus-postgresql", title="PostgreSQL", terms_json=[])
    db.add(area)
    await db.commit()
    await enable(db, learner)
    form = complete(focus_topic="postgresql")
    new = await client.post(
        "/api/knowledge-material/drafts", json=form, headers={"Idempotency-Key": str(uuid4())}
    )
    assert new.status_code == 200, new.text
    original = new.json()

    async def publish(draft):
        return await client.post(
            f"/api/curriculum/drafts/{draft['id']}/publish",
            json={"expected_version": draft["version"]},
        )

    assert (await publish(original)).status_code == 200
    slug = original["payload"]["skills"][0]["slug"]
    skill = await db.scalar(select(SkillNode).where(SkillNode.slug == slug))
    reading = f"/api/knowledge-material/skills/{skill.id}/reading"
    before = (await client.get(reading)).json()
    route = f"/api/knowledge-material/drafts/{original['id']}/factual-review"
    url = "https://example.org/manual"
    assert (await client.put(route, json={"urls": [url]})).status_code == 200
    quote = "Changing synthetic documentation."
    provider = FakeProvider(
        name="openai",
        structured={
            "findings": [
                {
                    "claim": "Reference changed",
                    "verdict": "needs_revision",
                    "source_index": 1,
                    "quote": quote,
                    "explanation": "Check the new guidance.",
                }
            ],
            "proposed_explanation": "Updated synthetic guidance.",
        },
    )
    client._transport.app.state.providers["openai"] = provider
    pages = iter(["one", "two", None, "two", "three"])

    async def fetch(requested):
        assert requested == url
        value = next(pages)
        if value is None:
            raise AppError("reference_unavailable", "Synthetic reference unreachable.", 502)
        return FetchedPage(
            raw=f"<main><p>{quote} {value}</p></main>".encode(), content_type="text/html"
        )

    monkeypatch.setattr("app.knowledge.reference_fetch.fetch", fetch)
    for _ in range(5):
        checked = await client.post(route + "/run")
        assert checked.status_code == 200, checked.text
    records = checked.json()["history"]
    assert [r["outcome"] for r in records] == [
        "reviewed",
        "reviewed",
        "failed",
        "sources_unchanged",
        "reviewed",
    ]
    assert records[2]["error"] == "reference_unavailable" and len(provider.calls) == 3
    assert records[0]["sources"][0]["sha256"] != records[1]["sources"][0]["sha256"]
    assert records[1]["sources"][0]["sha256"] == records[3]["sources"][0]["sha256"]

    async def propose(index):
        return await client.post(route + "/revisions/" + records[index]["id"])

    pending = (await propose(0)).json()
    selected = (await propose(1)).json()
    edition = dict(
        form, explanation="My edited factual explanation.", expected_version=selected["version"]
    )
    changed = await client.put("/api/knowledge-material/drafts/" + selected["id"], json=edition)
    assert changed.status_code == 200, changed.text
    assert changed.json()["payload"]["skills"][0]["slug"] == slug
    assert (await client.get(reading)).json() == before
    assert (await publish(changed.json())).status_code == 200
    after = (await client.get(reading)).json()
    assert after["draft_id"] == selected["id"] and after["explanation"] == edition["explanation"]
    assert after["learning_object_version"] == before["learning_object_version"] + 1
    await db.refresh(skill)
    assert skill.area_id == area.id
    stale = await propose(4)
    assert stale.status_code == 409 and stale.json()["error"]["code"] == "review_version_changed"
    superseded = await publish(pending)
    assert (
        superseded.status_code == 409
        and superseded.json()["error"]["code"] == "review_version_changed"
    )
    assert (await propose(1)).json()["id"] == selected["id"]
    assert (await client.get(reading)).json() == after
