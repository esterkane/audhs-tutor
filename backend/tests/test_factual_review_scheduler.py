import asyncio
from unittest.mock import AsyncMock

from app.core.factual_review_jobs import tick
from app.db.models import CurriculumDraft, KnowledgeReview
from tests.test_hybrid_authoring import enable


async def test_busy_reviews_leave_room_for_due_work(client, db, learner, settings, monkeypatch):
    await enable(db, learner)
    settings.save_authoring_key("synthetic-scheduler-fixture")
    eligible = []
    for index, lease in enumerate(["2999", "2999", "2999", "2000", None]):
        draft = CurriculumDraft(learner_id=learner.id, title="Synthetic", status="published")
        db.add(draft)
        await db.flush()
        db.add(
            KnowledgeReview(
                learner_id=learner.id,
                draft_id=draft.id,
                next_due_at=f"2001-01-0{index + 1}",
                running_until=lease,
            )
        )
        if index >= 3:
            eligible.append(draft.id)
    await db.commit()
    run = AsyncMock()
    monkeypatch.setattr("app.core.factual_review_jobs.run", run)
    client._transport.app.state.budget_lock = asyncio.Lock()
    await tick(client._transport.app)
    assert [call.args[-1] for call in run.await_args_list] == eligible
