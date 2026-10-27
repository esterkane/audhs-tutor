import asyncio

from sqlalchemy import func, select

from app.db.models import LearnerProfile
from app.kernel.learner import get_or_create_owner


async def test_concurrent_first_requests_share_one_owner(session_factory):
    async def resolve():
        async with session_factory() as db:
            return (await get_or_create_owner(db)).id

    identities = await asyncio.gather(*(resolve() for _ in range(12)))
    assert len(set(identities)) == 1
    async with session_factory() as db:
        assert await db.scalar(select(func.count()).select_from(LearnerProfile)) == 1


async def test_existing_owner_and_preferences_are_not_replaced(db, learner):
    learner.settings_json = {"preserve": "existing"}
    await db.commit()
    owner = await get_or_create_owner(db, "Different requested name")
    assert owner.id == learner.id and owner.display_name == "Test Learner"
    assert owner.settings_json == {"preserve": "existing"}
