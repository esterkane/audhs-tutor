from uuid import uuid4

import pytest
from sqlalchemy import select

from app.db.models import LearningObject, SkillNode
from app.kernel.knowledge_authoring import accepted_relationship
from tests.test_knowledge_authoring import complete

LINK = {"source": "A table grant", "link": "permits an operation on", "target": "a table"}


@pytest.mark.parametrize(
    "value",
    [None, {}, LINK | {"target": " A TABLE GRANT "}, LINK | {"link": " "}, LINK | {"extra": True}],
)
def test_only_complete_directed_relationships_are_revealed(value):
    assert accepted_relationship(value) is None


async def test_accepted_relationship_survives_prior_client_and_is_bound_to_reading(client, db):
    form = complete()
    response = await client.post(
        "/api/knowledge-material/drafts",
        headers={"Idempotency-Key": str(uuid4())},
        json=form | {"relationship": {"source": LINK["source"]}},
    )
    assert response.status_code == 200
    draft = response.json()

    async def save(d, fields):
        saved = await client.put(
            f"/api/knowledge-material/drafts/{d['id']}",
            json=form | fields | {"expected_version": d["version"]},
        )
        assert saved.status_code == 200, saved.text
        return saved.json()

    async def publish(d):
        return await client.post(
            f"/api/curriculum/drafts/{d['id']}/publish", json={"expected_version": d["version"]}
        )

    assert (await publish(draft)).status_code == 400
    draft = await save(await save(draft, {"relationship": LINK}), {})
    published = await publish(draft)
    assert published.status_code == 200, published.text
    accepted = published.json()["draft"]
    slug = accepted["payload"]["skills"][0]["slug"]
    node = await db.scalar(select(SkillNode).where(SkillNode.slug == slug))
    path = f"/api/knowledge-material/skills/{node.id}/reading"
    assert (await client.get(path)).json()["relationship"] == LINK
    revision = await client.post(
        f"/api/knowledge-material/drafts/{accepted['id']}/revise",
        json={"expected_version": accepted["version"]},
        headers={"Idempotency-Key": str(uuid4())},
    )
    changed = await save(revision.json(), {"relationship": None})
    assert (await client.get(path)).json()["relationship"] == LINK
    lo = await db.scalar(select(LearningObject).where(LearningObject.skill_id == node.id))
    lo.examples_json = ["Different underlying explanation", form["worked_example"]]
    await db.commit()
    assert (await client.get(path)).json()["relationship"] is None
    assert (await publish(changed)).status_code == 200
    assert (await client.get(path)).json()["relationship"] is None
