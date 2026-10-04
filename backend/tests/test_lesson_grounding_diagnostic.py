import importlib.util
from pathlib import Path

from sqlalchemy import select

from app.db.models import Chunk
from app.kernel import session as sessions
from app.orchestrator.lesson_evidence import snapshot
from app.orchestrator.playground import validate_lesson_origin
from app.orchestrator.tools import retrieve
from app.schemas.common import Mode


def diagnostic():
    path = Path(__file__).resolve().parents[2] / "scripts/eval_lesson_grounding.py"
    spec = importlib.util.spec_from_file_location("grounding_diagnostic", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


async def test_all_grounding_cases_are_isolated_validated_and_source_bound(db, learner):
    module = diagnostic()
    session = await sessions.start(db, learner.id, mode=Mode.STEADY, energy=3)
    assert len(module.FIXTURES) == 7
    for index, fixture in enumerate(module.FIXTURES):
        repo, body, criteria = await module.prepare(db, learner.id, session, index, fixture)
        await validate_lesson_origin(db, learner.id, body)
        result = await retrieve(repo, body.question, skill_id=body.lesson_origin.skill_id)
        evidence = snapshot(
            result, skill_id=body.lesson_origin.skill_id, title="Synthetic", goal="Reason"
        )
        assert bool(evidence.passages) == bool(fixture[1])
        assert all(p.text in fixture[1] for p in evidence.passages)
        assert criteria
        for passage in evidence.passages:
            assert (
                await db.scalar(select(Chunk.text).where(Chunk.id == passage.chunk_id))
                == passage.text
            )
