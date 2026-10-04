from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import KnowledgeArea, SkillEdge, SkillNode


async def test_area_map_scope_preserves_prerequisites_and_learning_state(
    client: AsyncClient, db: AsyncSession
) -> None:
    db.add_all(
        [
            KnowledgeArea(id="area-a", slug="area-a", title="Area A"),
            KnowledgeArea(id="area-b", slug="area-b", title="Area B"),
            KnowledgeArea(id="empty", slug="empty", title="Empty"),
        ]
    )
    await db.flush()
    db.add_all(
        [
            SkillNode(id="root", slug="root", title="Root", domain="test"),
            SkillNode(id="bridge", slug="bridge", title="Bridge", domain="test", area_id="area-b"),
            SkillNode(id="target", slug="target", title="Target", domain="test", area_id="area-a"),
            SkillNode(
                id="unrelated", slug="unrelated", title="Unrelated", domain="test", area_id="area-b"
            ),
        ]
    )
    await db.flush()
    db.add_all(
        [
            SkillEdge(from_skill_id="root", to_skill_id="bridge", kind="prerequisite"),
            SkillEdge(from_skill_id="bridge", to_skill_id="target", kind="prerequisite"),
            SkillEdge(from_skill_id="unrelated", to_skill_id="target", kind="related"),
        ]
    )
    await db.commit()
    before = (await client.get("/api/preferences")).json()
    whole = (await client.get("/api/skills/map")).json()
    response = await client.get("/api/skills/map", params={"area_id": "area-a"})
    assert response.status_code == 200
    scoped = response.json()
    assert scoped["area_title"] == "Area A"
    assert {n["id"] for n in scoped["nodes"]} == {"root", "bridge", "target"}
    assert {n["id"] for n in scoped["nodes"] if n["outside_area"]} == {"root", "bridge"}
    assert {(e["from"], e["to"]) for e in scoped["edges"]} == {
        ("root", "bridge"),
        ("bridge", "target"),
    }
    global_nodes = {n["id"]: n for n in whole["nodes"]}
    for node in scoped["nodes"]:
        for key in ("mastery", "memory", "unlocked", "is_next", "dimensions"):
            assert node[key] == global_nodes[node["id"]][key]
    assert "Unrelated" not in scoped["mermaid"]
    empty = (await client.get("/api/skills/map", params={"area_id": "empty"})).json()
    assert empty["nodes"] == [] and empty["edges"] == []
    assert (await client.get("/api/skills/map", params={"area_id": "missing"})).status_code == 404
    assert (await client.get("/api/preferences")).json() == before
    assert (await client.get("/api/skills/map")).json() == whole
