"""Real process exits must not turn uncertain grading into automatic regrading."""

import asyncio
import json
import sys
import uuid
from pathlib import Path

import pytest
from sqlalchemy import func, select

from app.db import models
from app.kernel.seed import load_seed
from app.models_ai import registry

SEED = Path(__file__).resolve().parents[2] / "seeds" / "attention"


@pytest.mark.parametrize("owned", [False, True])
@pytest.mark.parametrize("phase", ["prepared", "inference_started"])
async def test_hard_exit_preserves_claim_without_regrading(client, db, db_path, phase, owned):
    await load_seed(db, SEED)
    await registry.seed_defaults(db, installed_ollama_tags={"llama3.1:8b"})
    session = (await client.post("/api/sessions", json={"mode": "steady", "energy": 3})).json()
    item = (await client.get("/api/assess/next", params={"session_id": session["id"]})).json()[
        "item"
    ]
    body = {
        "session_id": session["id"],
        "assessment_id": item["id"],
        "answer": "0",
        "content_version": item["content_version"],
    }
    row = await db.get(models.Session, session["id"])
    owner = row.learner_id
    await db.rollback()  # Release the parent read transaction before the child writes.
    key = str(uuid.uuid4())
    child = """
import asyncio, json, os, sys
from app.db.session import make_engine, make_session_factory
from app.db import workspace_requests, assessment_executions
from app.orchestrator import assessment_content
from app.schemas.grading import AttemptRequest
from app.orchestrator.assessment_guard import AssessmentGuard
from pathlib import Path

async def main():
    engine = make_engine('sqlite+aiosqlite:///' + sys.argv[1])
    async with make_session_factory(engine)() as db:
        body = AttemptRequest.model_validate(json.loads(sys.argv[3]))
        claim, saved = await workspace_requests.claim(
            db, sys.argv[2], body.session_id, 'assessment:' + sys.argv[4], body.model_dump(mode='json')
        )
        assert saved is None
        guard = AssessmentGuard.create(Path(sys.argv[1]), claim) if sys.argv[6] == "yes" else None
        content = await assessment_content.snapshot(db, body.assessment_id)
        await assessment_executions.prepare(
            db, sys.argv[2], claim, request_json=body.model_dump(mode='json'),
            content_fingerprint=assessment_content.recovery_fingerprint(content),
            owner_json=guard.receipt if guard else None,
        )
        if sys.argv[5] == 'inference_started':
            if guard: guard.seal_inference()
            await assessment_executions.mark_inference_started(db, sys.argv[2], claim)
        os._exit(77)
asyncio.run(main())
"""
    process = await asyncio.create_subprocess_exec(
        sys.executable,
        "-c",
        child,
        str(db_path),
        owner,
        json.dumps(body),
        key,
        phase,
        "yes" if owned else "no",
    )
    try:
        assert await asyncio.wait_for(process.wait(), 20) == 77
    finally:
        if process.returncode is None:
            process.kill()
            await process.wait()
    state = await client.get(f"/api/assess/requests/{key}", params={"session_id": session["id"]})
    eligible = owned and phase == "prepared"
    assert state.status_code == 200
    assert state.json()["status"] == ("prepared_ready" if eligible else "unresolved")
    retry = await client.post("/api/assess/attempt", json=body, headers={"Idempotency-Key": key})
    assert retry.status_code == 409 and retry.json()["error"]["code"] == "request_unresolved"
    assert await db.scalar(select(func.count()).select_from(models.WorkspaceRequest)) == 1
    execution = await db.scalar(select(models.AssessmentExecution))
    assert execution.phase == phase and execution.grade_json is None
    for table in (
        models.AssessmentAttempt,
        models.CompetencyEvidence,
        models.ModelCall,
        models.TutorAnswer,
    ):
        assert await db.scalar(select(func.count()).select_from(table)) == 0

    continued = await client.post(
        f"/api/assess/requests/{key}/continue", params={"session_id": session["id"]}
    )
    assert continued.status_code == (200 if eligible else 409), continued.text
    assert await db.scalar(select(func.count()).select_from(models.AssessmentAttempt)) == int(
        eligible
    )
    assert await db.scalar(select(func.count()).select_from(models.CompetencyEvidence)) == int(
        eligible
    )
    assert await db.scalar(select(func.count()).select_from(models.ModelCall)) == 0
