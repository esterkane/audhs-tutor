from sqlalchemy import func, select

from app.db.models import KnowledgeArea, LearnerProfile, ReviewItem, Session, SkillNode
from app.kernel import areas, focus_reset, skill_graph


async def test_reset_is_idempotent_and_retains_history_and_other_owners(db, learner):
    learner_id = learner.id
    other = LearnerProfile(display_name="Other")
    skill = SkillNode(
        slug="historical",
        title="Historical lesson",
        domain="programming",
        created_at="2026-10-01T00:00:00+00:00",
    )
    db.add_all([other, skill])
    await db.commit()
    session = Session(learner_id=learner_id, mode="steady", energy=3)
    own = ReviewItem(learner_id=learner_id, skill_id=skill.id, item_type="recall", prompt_json={})
    foreign = ReviewItem(learner_id=other.id, skill_id=skill.id, item_type="recall", prompt_json={})
    db.add_all([session, own, foreign])
    await db.commit()
    cutoff = await focus_reset.apply(db, learner_id)
    assert await focus_reset.apply(db, learner_id) == cutoff
    await db.refresh(own)
    await db.refresh(foreign)
    await db.refresh(session)
    assert not own.active and foreign.active
    assert session.ended_at == cutoff
    assert await db.scalar(select(func.count()).select_from(Session)) == 1
    assert await db.get(SkillNode, skill.id) is not None
    assert not await skill_graph.all_nodes(db, learner_id=learner_id)
    catalogue = await areas.catalogue(db, learner_id)
    assert await db.scalar(select(func.count()).select_from(KnowledgeArea)) == 6
    assert len(catalogue["areas"]) == 6
