import asyncio

from sqlalchemy import func, select

from app.api.deps import get_learner
from app.db.models import AuthoredVisualVersion, LearnerProfile, ModelCall, VisualGenerationRequest
from app.models_ai.fake import FakeProvider
from tests.test_visual_generation_worker import setup


async def prepare(client, db, learner, session_factory):
    row, proposal = await setup(db, learner, session_factory)
    app = client._transport.app
    app.state.providers = {"ollama": FakeProvider(structured=proposal.model_dump())}
    target = (await client.get("/api/authored-visuals/answer-target/root")).json()
    return app, row, {"binding": target["binding"]}


async def settle(app):
    await asyncio.wait_for(asyncio.gather(*list(app.state.visual_jobs.tasks.values())), 5)


async def test_start_duplicate_poll_reopen_and_cancel_completed(
    client, db, learner, session_factory
):
    app, _, body = await prepare(client, db, learner, session_factory)
    responses = await asyncio.gather(
        *[
            client.post("/api/visual-generation", json=body, headers={"Idempotency-Key": "start"})
            for _ in range(2)
        ]
    )
    assert all(r.status_code == 202 for r in responses)
    identity = responses[0].json()["id"]
    assert responses[1].json()["id"] == identity
    await settle(app)
    path = f"/api/visual-generation/{identity}"
    result = (await client.get(path)).json()
    assert result["state"] == "completed"
    assert result["document_id"] and result["result_version_id"]
    assert "worker_token" not in result and "binding_json" not in result
    assert (await client.post(path + "/cancel")).json()["state"] == "completed"
    assert (await client.get("/api/visual-generation?answer_id=root")).json()[0] == result
    assert (
        await client.get(
            f"/api/authored-visuals/{result['document_id']}/versions/{result['result_version_id']}"
        )
    ).status_code == 200
    assert len(app.state.providers["ollama"].calls) == 1
    assert await db.scalar(select(func.count()).select_from(AuthoredVisualVersion)) == 1


async def test_stop_inflight_and_replay_never_restarts(client, db, learner, session_factory):
    app, _, body = await prepare(client, db, learner, session_factory)
    started = asyncio.Event()

    class Waiting(FakeProvider):
        async def complete(self, *args, **kwargs):
            started.set()
            await asyncio.Event().wait()

    app.state.providers = {"ollama": Waiting()}
    response = await client.post(
        "/api/visual-generation", json=body, headers={"Idempotency-Key": "stop"}
    )
    identity = response.json()["id"]
    await asyncio.wait_for(started.wait(), 5)
    response = await client.post(f"/api/visual-generation/{identity}/cancel")
    assert response.json()["state"] == "cancelled"
    await app.state.visual_jobs.close()
    app.state.visual_jobs.closing = False
    replay = await client.post(
        "/api/visual-generation", json=body, headers={"Idempotency-Key": "stop"}
    )
    assert replay.json()["state"] == "cancelled"
    assert not app.state.visual_jobs.tasks
    assert await db.scalar(select(func.count()).select_from(AuthoredVisualVersion)) == 0


async def test_status_is_read_only_and_scoped(client, db, learner, session_factory):
    app, row, body = await prepare(client, db, learner, session_factory)
    path = f"/api/visual-generation/{row.id}"
    assert (await client.get(path)).json()["state"] == "pending"
    assert not app.state.visual_jobs.tasks
    assert await db.scalar(select(func.count()).select_from(ModelCall)) == 0
    other = LearnerProfile(display_name="Other")
    db.add(other)
    await db.commit()

    async def owner():
        return other

    app.dependency_overrides[get_learner] = owner
    assert (await client.get(path)).status_code == 404
    assert (await client.post(path + "/cancel")).status_code == 404
    assert (await client.get("/api/visual-generation?answer_id=root")).json() == []
    denied = await client.post(
        "/api/visual-generation", json=body, headers={"Idempotency-Key": "foreign"}
    )
    assert denied.status_code == 404
    assert not app.state.visual_jobs.tasks


async def test_invalid_and_conflicting_requests_are_not_dispatched(
    client, db, learner, session_factory
):
    app, row, body = await prepare(client, db, learner, session_factory)
    for invalid in [{**body, "prompt_version": "override"}, {"binding": "PRIVATE_SENTINEL"}]:
        result = await client.post(
            "/api/visual-generation", json=invalid, headers={"Idempotency-Key": "bad"}
        )
        assert result.status_code == 422
        assert "PRIVATE_SENTINEL" not in result.text
    result = await client.post(
        "/api/visual-generation", content=b"x" * 131_073, headers={"Idempotency-Key": "large"}
    )
    assert result.status_code == 413
    body["binding"]["learning_purpose"] = "Changed payload"
    result = await client.post(
        "/api/visual-generation", json=body, headers={"Idempotency-Key": "worker"}
    )
    assert result.status_code == 409
    assert not app.state.visual_jobs.tasks
    assert await db.scalar(select(func.count()).select_from(VisualGenerationRequest)) == 1


async def test_shutdown_stops_workers_and_refuses_new_start(client, db, learner, session_factory):
    app, _, body = await prepare(client, db, learner, session_factory)
    started = asyncio.Event()

    class Waiting(FakeProvider):
        async def complete(self, *args, **kwargs):
            started.set()
            await asyncio.Event().wait()

    app.state.providers = {"ollama": Waiting()}
    result = await client.post(
        "/api/visual-generation", json=body, headers={"Idempotency-Key": "shutdown"}
    )
    identity = result.json()["id"]
    await asyncio.wait_for(started.wait(), 5)
    await app.state.visual_jobs.close()
    assert not app.state.visual_jobs.tasks
    assert (await client.get(f"/api/visual-generation/{identity}")).json()["state"] == "cancelled"
    assert (
        await client.post("/api/visual-generation", json=body, headers={"Idempotency-Key": "after"})
    ).status_code == 503


async def test_prompt_upgrade_does_not_change_existing_retry_identity(
    client, db, learner, session_factory
):
    from app.kernel.visual_generation import GenerationRequests
    from app.schemas.answer_visual_binding import AnswerVisualBinding

    app, _, body = await prepare(client, db, learner, session_factory)
    repo = GenerationRequests(session_factory)
    old = await repo.reserve(
        learner.id,
        "old-prompt",
        AnswerVisualBinding.model_validate(body["binding"]),
        "ask.visual.older",
    )
    await repo.cancel(learner.id, old.id)
    replay = await client.post(
        "/api/visual-generation", json=body, headers={"Idempotency-Key": "old-prompt"}
    )
    assert replay.status_code == 202
    assert replay.json()["id"] == old.id
    assert replay.json()["state"] == "cancelled"
    assert not app.state.visual_jobs.tasks
    body["binding"]["learning_purpose"] = "Different intent"
    conflict = await client.post(
        "/api/visual-generation", json=body, headers={"Idempotency-Key": "old-prompt"}
    )
    assert conflict.status_code == 409
