"""Shared curriculum writers cannot adopt private identifiers or expose private course counts."""

import pytest
import yaml
from sqlalchemy import func, select

from app.core.errors import AppError
from app.db.models import CurriculumDraft, LearnerProfile, SkillNode
from app.kernel import curriculum, listening, practice, seed, vocab_import


def payload(slugs):
    return {
        "domain": "ai_ml",
        "skills": [{"slug": s, "title": "Shared title", "prerequisites": []} for s in slugs],
        "learning_objects": [
            {"skill": s, "concept": "Mean", "goal": "Explain the mean"} for s in slugs
        ],
        "assessments": [
            {
                "skill": s,
                "kind": "mcq",
                "item": {
                    "question": "What is the mean of 2 and 4?",
                    "options": ["3", "6"],
                    "answer": 0,
                },
            }
            for s in slugs
        ],
    }


async def test_private_course_counts_and_prerequisites_are_scoped(db, learner):
    db.add(LearnerProfile(id="other", display_name="Other"))
    await db.flush()
    for slug, owner in [("shared", None), ("own", learner.id), ("foreign", "other")]:
        db.add(
            SkillNode(slug=slug, title=slug, course=slug, domain="ai_ml", owner_learner_id=owner)
        )
    await db.commit()
    rows = await curriculum.material_status(db, learner.id)
    assert {r["course"] for r in rows} == {"shared", "own"}
    p = payload(["new"])
    for prerequisite, allowed in [("shared", True), ("own", False), ("foreign", False)]:
        p["skills"][0]["prerequisites"] = [prerequisite]
        errors = [e for e in await curriculum.validate_payload(db, p) if e.level == "error"]
        assert (not errors) == allowed


@pytest.mark.parametrize("same_owner", [False, True])
async def test_shared_writers_refuse_private_collisions_before_mutation(
    db, learner, tmp_path, same_owner
):
    db.add(LearnerProfile(id="other", display_name="Other"))
    await db.flush()
    owner = learner.id if same_owner else "other"
    slugs = ["private-target", practice.deck_slug("de"), listening.listening_slug("de")]
    for slug in slugs:
        db.add(SkillNode(slug=slug, title="Keep private", domain="ai_ml", owner_learner_id=owner))
    await db.commit()
    before = await db.scalar(select(func.count()).select_from(SkillNode))
    for fn in [practice.vocab_deck, listening.listening_node]:
        with pytest.raises(AppError) as error:
            await fn(db, "de")
        assert error.value.http_status == 409
    assert await vocab_import.existing_refs(db, learner.id, "de") == set()
    p = payload(["would-be-created-first", "private-target"])
    (tmp_path / "skills.yaml").write_text(yaml.safe_dump(p))
    with pytest.raises(AppError):
        await seed.load_seed(db, tmp_path)
    draft = CurriculumDraft(learner_id=learner.id, title="Draft", payload_json=p)
    db.add(draft)
    await db.commit()
    with pytest.raises(AppError):
        await curriculum.publish_draft(db, learner.id, draft.id, expected_version=1)
    # Even an explicit subsequent commit must not persist earlier partial writes.
    await db.commit()
    assert await db.scalar(select(func.count()).select_from(SkillNode)) == before
    assert {n.title for n in await db.scalars(select(SkillNode))} == {"Keep private"}
    await db.refresh(draft)
    assert draft.status == "draft" and draft.version == 1
