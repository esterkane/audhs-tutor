from uuid import uuid4

from sqlalchemy import func, select

from app.db import models, workspace_requests
from app.voice.recovery import key


async def test_voice_lookup_is_read_only_owner_scoped_and_preserves_unresolved(client, db, learner):
    session = models.Session(learner_id=learner.id, mode="steady", energy=3)
    other = models.LearnerProfile(display_name="Other")
    db.add_all([session, other])
    await db.flush()
    foreign = models.Session(learner_id=other.id, mode="steady", energy=3)
    db.add(foreign)
    await db.commit()
    identity = str(uuid4())
    url = f"/api/voice/requests/{identity}"
    assert (await client.get(url, params={"session_id": session.id})).json()[
        "status"
    ] == "not_found"
    assert await db.scalar(select(func.count()).select_from(models.WorkspaceRequest)) == 0
    claim, _ = await workspace_requests.claim(
        db, learner.id, session.id, key(identity), {"surface": "voice_turn"}
    )
    response = await client.get(url, params={"session_id": session.id})
    assert response.json()["status"] == "unresolved"
    assert response.json()["text"] is None
    assert (await client.get(url, params={"session_id": foreign.id})).status_code == 404
    await workspace_requests.complete(
        db,
        learner.id,
        claim,
        {
            "request_id": identity,
            "status": "partial",
            "text": "Partial words",
            "transcript": "Question",
            "interrupted": True,
        },
    )
    response = await client.get(url, params={"session_id": session.id})
    assert response.json()["status"] == "partial"
    assert response.json()["text"] == "Partial words"
    assert await db.scalar(select(func.count()).select_from(models.ModelCall)) == 0


async def test_interrupt_during_claim_never_starts_generation(db, learner, monkeypatch):
    import asyncio
    import json
    from unittest.mock import AsyncMock, Mock

    from app.voice.loop import VoiceLoop, VoiceState, _request_identity
    from app.voice.recovery import lookup

    session = models.Session(learner_id=learner.id, mode="steady", energy=3)
    db.add(session)
    await db.commit()
    original = workspace_requests.claim
    entered, release = asyncio.Event(), asyncio.Event()

    async def delayed(*args, **kwargs):
        result = await original(*args, **kwargs)
        entered.set()
        await release.wait()
        return result

    monkeypatch.setattr(workspace_requests, "claim", delayed)
    turn, tts = Mock(), Mock()
    loop = VoiceLoop(
        db, turn, stt=None, tts=tts, vad=Mock(), voice_dir=Mock(), learner_id=learner.id
    )
    state = VoiceState(
        session_id=session.id,
        skill_id=None,
        lang=None,
        text_only=False,
        conversation=False,
        voice="",
    )
    ws = Mock()
    ws.send_text = AsyncMock()
    identity = str(uuid4())
    token = _request_identity.set(identity)
    try:
        task = asyncio.create_task(loop._respond(ws, state, "Question", stt_ms=0))
    finally:
        _request_identity.reset(token)
    await entered.wait()
    loop._interrupted.set()
    release.set()
    await task
    turn.run.assert_not_called()
    assert not tts.mock_calls
    assert loop._speak_task is None
    stored = await lookup(db, learner.id, session.id, identity)
    assert stored.status == "partial" and stored.interrupted is True and stored.text == ""
    sent = [json.loads(call.args[0]) for call in ws.send_text.await_args_list]
    assert [message["type"] for message in sent] == ["done"]
    assert sent[0]["latency"]["interrupted"] is True
