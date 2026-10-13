"""Private lesson context and cached explanations must never cross owner scope."""

import pytest
from sqlalchemy import func, select

from app.core.errors import AppError
from app.db.models import (
    LearnerProfile,
    LearningEvent,
    LearningObject,
    Representation,
    Session,
    SkillNode,
)
from app.kernel import representations as cache
from app.orchestrator import representations, tools


async def test_private_context_cache_and_preference_access(db, learner, client, fake_local):
    db.add(LearnerProfile(id="other", display_name="Other", created_at="2999-01-01"))
    await db.flush()
    for prefix, owner in [("own", learner.id), ("foreign", "other")]:
        db.add(
            SkillNode(id=prefix, slug=prefix, title=prefix, domain="ai_ml", owner_learner_id=owner)
        )
    await db.flush()
    for prefix in ["own", "foreign"]:
        db.add(
            LearningObject(
                id=f"{prefix}-object", skill_id=prefix, concept=prefix, goal=f"{prefix} goal"
            )
        )
    await db.flush()
    for prefix in ["own", "foreign"]:
        db.add(
            Representation(
                id=f"{prefix}-view",
                object_id=f"{prefix}-object",
                kind="analogy",
                content=f"{prefix} text",
            )
        )
    session = Session(learner_id=learner.id, mode="steady", energy=3)
    db.add(session)
    await db.commit()
    own = await db.get(SkillNode, "own")
    foreign = await db.get(SkillNode, "foreign")
    assert (await tools.get_learning_contract(db, own, learner_id=learner.id))[
        "objective"
    ] == "own goal"
    for scope in [None, learner.id]:
        with pytest.raises(KeyError):
            await tools.get_learning_contract(db, foreign, learner_id=scope)
        assert await cache.get_cached(db, "foreign-object", "analogy", learner_id=scope) is None
        assert await cache.cached_kinds(db, "foreign-object", learner_id=scope) == set()
        assert await cache.object_for_skill(db, "foreign", learner_id=scope) is None
        with pytest.raises(AppError):
            await cache.store(
                db, "foreign-object", "analogy", "overwrite", model_call_id=None, learner_id=scope
            )
        with pytest.raises(AppError):
            await cache.invalidate(db, "foreign-object", learner_id=scope)
    assert (
        await cache.get_cached(db, "own-object", "analogy", learner_id=learner.id)
    ).content == "own text"
    assert await cache.get_cached(db, "own-object", "analogy") is None
    before = await db.scalar(select(func.count()).select_from(LearningEvent))
    with pytest.raises(AppError):
        await representations.prefer(db, session, "own-view", "foreign-view")
    assert await db.scalar(select(func.count()).select_from(LearningEvent)) == before
    assert (await client.get("/api/sessions/selection/own")).status_code == 200
    assert (await client.get("/api/sessions/selection/foreign")).status_code == 404
    assert (await client.get("/api/objects/own/representations")).status_code == 200
    assert (await client.get("/api/objects/foreign/representations")).status_code == 404
    assert (await db.get(Representation, "foreign-view")).content == "foreign text"

    response = await client.post(
        "/api/tutor/turn",
        json={"session_id": session.id, "skill_id": "foreign", "text": "Explain this lesson"},
    )
    assert response.status_code == 404
    assert fake_local.calls == []
    assert await db.scalar(select(func.count()).select_from(LearningEvent)) == before

    for target, chosen in [("foreign", "own-view"), ("own", "foreign-view")]:
        denied = await client.post(
            f"/api/objects/{target}/representations/prefer",
            json={"session_id": session.id, "chosen_id": chosen, "rejected_id": "own-view"},
        )
        assert denied.status_code == 404
    with pytest.raises(ValueError, match="from this lesson"):
        await representations.prefer(db, session, "own-view", "own-view", skill_id="foreign")
    assert await db.scalar(select(func.count()).select_from(LearningEvent)) == before
