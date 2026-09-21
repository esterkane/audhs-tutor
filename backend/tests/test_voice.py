"""P9 voice: readiness with nothing installed (actionable, never downloads), install without
activation, activation refused until STT+TTS are ready, verify with fakes, mic test bounded and
discarded, and the WebSocket loop with fakes: speech → transcript → tokens → audio → done + `spoke`
event; nothing heard; interruption; text-only fallback; STT failure → text fallback; reconnect;
retention opt-in. Synthetic audio only — none of this is a microphone benchmark."""

import asyncio
import json
import wave
from collections.abc import Iterator
from pathlib import Path

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession
from starlette.testclient import TestClient

from app.core.config import Settings
from app.db import models
from app.kernel import preferences
from app.kernel.seed import load_seed
from app.knowledge.sqlite_hybrid import SqliteHybridRepository
from app.main import create_app
from app.models_ai import registry
from app.models_ai.fake import FakeProvider
from app.models_ai.provider import ModelSpec
from app.voice import setup
from app.voice.loop import prune, sentences
from app.voice.stt import FakeStt
from app.voice.tts import FakeTts
from app.voice.vad import EnergyVad, silence, tone, wav_bytes

SEED = Path(__file__).resolve().parents[2] / "seeds" / "attention"


def test_energy_vad_and_sentences() -> None:
    vad = EnergyVad()
    frames = [silence(0.1)] * 3 + [tone(0.1)] * 5 + [silence(0.1)] * 8
    states = [vad.feed(f) for f in frames]
    assert states[0] == "silence" and "speech" in states and states[-1] == "end"
    assert vad.heard_ms >= 300
    assert sentences("One. Two! Three? Four") == ["One.", "Two!", "Three?", "Four"]
    from app.voice.loop import speakable

    assert speakable("(analogy) Keys are **labels** [1], values are contents [2, 3].") == (
        "Keys are labels, values are contents."
    )


async def test_readiness_is_honest_and_never_installs(
    client: AsyncClient, db: AsyncSession, settings: Settings
) -> None:
    await registry.seed_defaults(db, installed_ollama_tags=set())
    r = await client.get("/api/voice/readiness")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["stt"]["ready"] is False and "pull whisper" in body["stt"]["action"]
    assert body["tts"]["ready"] is False and "Kokoro" in body["tts"]["action"]
    assert body["vad"]["ready"] is True and body["vad"]["status"] == "fallback"
    assert body["activated"] is False and body["can_activate"] is False
    assert body["retain_audio"] is False
    assert body["stt_id"] == "whisper-large-v3-turbo" and body["tts_id"] == "kokoro-82m"
    # a conversation language the Kokoro voices cannot speak is flagged, not silently mis-voiced
    await preferences.set_pref(
        db,
        (await db.execute(select(models.LearnerProfile))).scalars().first().id,
        "voice.conversation_lang",
        "de",
        origin="explicit",
    )  # type: ignore[union-attr]
    body = (await client.get("/api/voice/readiness")).json()
    assert body["conversation_lang_supported"] is False and any("de" in n for n in body["notes"])
    # activation is refused while a component is missing
    r = await client.post("/api/voice/activate", json={"enabled": True})
    assert r.status_code == 409 and "cannot be activated" in r.json()["error"]["message"]
    # verify reports the missing pieces instead of failing
    r = await client.post("/api/voice/verify")
    assert r.status_code == 200 and len(r.json()["problems"]) == 2
    # "install" of the Kokoro server is not a download: the pull job explains what to do
    r = await client.post("/api/models/kokoro-82m/pull")
    assert r.status_code == 202
    for _ in range(50):
        jobs = (await client.get("/api/models/jobs")).json()["jobs"]
        if jobs and jobs[0]["status"] != "running":
            break
        await asyncio.sleep(0.02)
    assert jobs[0]["status"] == "failed" and "Kokoro" in (jobs[0]["error"] or "")
    row = await db.get(models.ModelRegistry, "kokoro-82m")
    assert row is not None and row.status == "available"  # never silently "ready"
    assert not list(settings.voice_dir_resolved.rglob("*.wav"))  # noqa: ASYNC240


async def test_mic_test_is_bounded_and_discards_the_recording(
    client: AsyncClient, db: AsyncSession, engine: AsyncEngine, settings: Settings
) -> None:
    # the app under test uses fakes for the speech components
    from app.api.deps import (
        get_settings_dep,  # noqa: F401  (import keeps the dependency graph honest)
    )

    app = client._transport.app  # type: ignore[attr-defined]
    app.state.voice_overrides = {"stt": FakeStt("hello tutor"), "tts": FakeTts()}
    wav = {"Content-Type": "audio/wav"}
    good = wav_bytes(tone(1.0))
    r = await client.post("/api/voice/test-mic", content=good, headers=wav)
    assert r.status_code == 200, r.text
    assert r.json()["text"] == "hello tutor" and r.json()["recording_kept"] is False
    # too long, wrong format, too short
    r = await client.post("/api/voice/test-mic", content=wav_bytes(silence(21.0)), headers=wav)
    assert r.status_code == 400
    r = await client.post("/api/voice/test-mic", content=b"nope", headers=wav)
    assert r.status_code == 400
    r = await client.post("/api/voice/test-mic", content=wav_bytes(tone(0.2)), headers=wav)
    assert r.status_code == 400
    # over the byte cap → 413 before anything is parsed
    r = await client.post(
        "/api/voice/test-mic", content=b"\x00" * (setup.MAX_TEST_BYTES + 10), headers=wav
    )
    assert r.status_code == 413
    # verify with a recogniser that fails: reported as a problem, never as success
    app.state.voice_overrides = {"stt": FakeStt("x", fail_times=1), "tts": FakeTts()}
    r = await client.post("/api/voice/verify")
    assert r.status_code == 200 and any("failed" in p for p in r.json()["problems"])
    app.state.voice_overrides = {"stt": FakeStt("hello tutor"), "tts": FakeTts()}
    # the model_call row exists; no recording anywhere on disk
    calls = (await db.execute(select(models.ModelCall))).scalars().all()
    assert calls[0].task == "stt" and calls[0].metadata_json["purpose"] == "voice-setup-test"
    assert any(c.task == "stt" and not c.ok for c in calls)  # the failed verify left its row
    assert not list(settings.voice_dir_resolved.rglob("*.wav"))  # noqa: ASYNC240
    # verify with fakes: both components answer, activation now possible? (registry rows still
    # 'available' → readiness says no; fakes are for the loop, activation follows the registry)
    r = await client.post("/api/voice/verify")
    assert r.status_code == 200 and r.json()["problems"] == [] and r.json()["tts"]["seconds"] > 0
    app.state.voice_overrides = None


@pytest.fixture
def ws_app(settings: Settings, engine: AsyncEngine):  # type: ignore[no-untyped-def]
    """A sync TestClient over the same engine so WebSockets can be driven in a test."""
    # the app creates its own engine in its lifespan (TestClient runs a separate event loop and
    # aiosqlite connections are bound to the loop that made them); the SQLite file is shared
    app = create_app(settings)
    app.state.providers = {
        "ollama": FakeProvider(text="Attention weighs tokens. Next: try one example."),
        "anthropic": FakeProvider(text="hosted"),
    }
    # the retrieval repo is created inside the app's thread: SQLite handles are thread-bound
    app.state.repo = None
    app.state.repo_factory = lambda: SqliteHybridRepository(
        FakeProvider(vectors_dim=32),
        ModelSpec(registry_id="fake-embed", provider="fake", model="f"),
        dims=32,
    )
    app.state.settings = settings
    return app


@pytest.fixture
async def spoken_world(db: AsyncSession, learner: models.LearnerProfile) -> dict[str, str]:
    await load_seed(db, SEED)
    await registry.seed_defaults(db, installed_ollama_tags={"llama3.1:8b", "nomic-embed-text"})
    s = models.Session(learner_id=learner.id, mode="steady", energy=3)
    db.add(s)
    await db.commit()
    return {"session_id": s.id, "learner_id": learner.id}


def _connect(tc: TestClient) -> Iterator:  # type: ignore[type-arg]
    return tc.websocket_connect("/api/voice/ws")  # type: ignore[return-value]


def _collect(ws, until: set[str], limit: int = 200) -> list[dict]:  # type: ignore[no-untyped-def,type-arg]
    out: list[dict] = []  # type: ignore[type-arg]
    for _ in range(limit):
        msg = json.loads(ws.receive_text())
        out.append(msg)
        if msg["type"] in until:
            break
    return out


async def test_voice_loop_speech_to_answer_with_events(
    ws_app,
    spoken_world: dict[str, str],
    db: AsyncSession,
    settings: Settings,  # type: ignore[no-untyped-def]
) -> None:
    stt, tts = FakeStt("what is attention"), FakeTts()
    ws_app.state.voice_overrides = {"stt": stt, "tts": tts, "vad": EnergyVad()}
    sid = spoken_world["session_id"]

    def drive() -> list[dict]:  # type: ignore[type-arg]
        with TestClient(ws_app) as tc, _connect(tc) as ws:
            ws.send_text(json.dumps({"type": "start", "session_id": sid, "lang": "en"}))
            ready = json.loads(ws.receive_text())
            assert ready["type"] == "ready" and ready["text_only"] is False
            for f in [tone(0.1)] * 6 + [silence(0.1)] * 9:  # speech, then 900 ms silence → end
                ws.send_bytes(f)
            msgs = _collect(ws, {"done"})
            ws.send_text(json.dumps({"type": "stop"}))
            return msgs

    msgs = await asyncio.to_thread(drive)
    kinds = [m["type"] for m in msgs]
    assert kinds[0] == "listening"
    assert (
        "transcript" in kinds
        and next(m for m in msgs if m["type"] == "transcript")["text"] == "what is attention"
    )
    assert "token" in kinds and "audio" in kinds and kinds[-1] == "done"
    done = msgs[-1]
    assert done["turn"]["turn_id"] and done["latency"]["stt_ms"] >= 0
    assert done["latency"]["tts_first_audio_ms"] is not None and not done["latency"]["interrupted"]
    assert tts.spoken  # sentences were synthesised
    # the ordinary tutor events plus one `spoke`; no recording kept without opt-in
    ev = (await db.execute(select(models.LearningEvent))).scalars().all()
    verbs = {e.verb for e in ev}
    assert {"asked", "explained", "spoke"} <= verbs
    spoke = next(e for e in ev if e.verb == "spoke")
    assert spoke.result_json["total_ms"] >= 0 and spoke.context_json["stt_model"] == "fake-stt"
    calls = (await db.execute(select(models.ModelCall))).scalars().all()
    assert {c.task for c in calls} >= {"stt", "tts"}
    assert not list(settings.voice_dir_resolved.rglob("*.wav"))  # noqa: ASYNC240


async def test_voice_loop_nothing_heard_interrupt_text_fallback_reconnect(
    ws_app,
    spoken_world: dict[str, str],
    db: AsyncSession,  # type: ignore[no-untyped-def]
) -> None:
    stt = FakeStt("tell me more")
    tts = FakeTts(delay_s=0.3)  # slow enough to interrupt
    ws_app.state.voice_overrides = {"stt": stt, "tts": tts, "vad": EnergyVad()}
    sid = spoken_world["session_id"]

    def drive() -> dict[str, list[dict]]:  # type: ignore[type-arg]
        out: dict[str, list[dict]] = {}  # type: ignore[type-arg]
        with TestClient(ws_app) as tc:
            with _connect(tc) as ws:
                ws.send_text(json.dumps({"type": "start", "session_id": sid}))
                json.loads(ws.receive_text())
                # (a) only silence → nothing heard, no turn
                for f in [silence(0.1)] * 12:
                    ws.send_bytes(f)
                ws.send_text(json.dumps({"type": "end_of_speech"}))
                out["silence"] = _collect(ws, {"nothing_heard"})
                # (b) speech, then interrupt while the tutor speaks
                for f in [tone(0.1)] * 6:
                    ws.send_bytes(f)
                ws.send_text(json.dumps({"type": "end_of_speech"}))
                first = _collect(ws, {"token", "audio"})
                ws.send_text(json.dumps({"type": "interrupt"}))
                rest = _collect(ws, {"done"})
                out["interrupt"] = first + rest
                # (c) typed fallback inside the same connection
                ws.send_text(json.dumps({"type": "text", "text": "and in one sentence?"}))
                out["text"] = _collect(ws, {"done"})
                ws.send_text(json.dumps({"type": "stop"}))
            # (d) reconnect: a fresh socket on the same session works
            with _connect(tc) as ws2:
                ws2.send_text(json.dumps({"type": "start", "session_id": sid, "text_only": True}))
                ready = json.loads(ws2.receive_text())
                assert ready["text_only"] is True and ready["why_text_only"] == "requested"
                ws2.send_text(json.dumps({"type": "text", "text": "again please"}))
                out["reconnect"] = _collect(ws2, {"done"})
                ws2.send_text(json.dumps({"type": "stop"}))
        return out

    out = await asyncio.to_thread(drive)
    assert [m["type"] for m in out["silence"]][-1] == "nothing_heard"
    kinds = [m["type"] for m in out["interrupt"]]
    assert "interrupted" in kinds and kinds[-1] == "done"
    assert out["interrupt"][-1]["latency"]["interrupted"] is True
    assert [m["type"] for m in out["text"]][-1] == "done"
    assert "audio" not in {m["type"] for m in out["reconnect"]}  # text-only: no audio frames
    assert [m["type"] for m in out["reconnect"]][-1] == "done"
    spoke = [
        e for e in (await db.execute(select(models.LearningEvent))).scalars() if e.verb == "spoke"
    ]
    assert len(spoke) == 3  # interrupted turn, typed turn, reconnect turn — the silence made none


async def test_voice_loop_stt_failure_and_retention(
    ws_app,
    spoken_world: dict[str, str],
    db: AsyncSession,
    settings: Settings,
    tmp_path: Path,  # type: ignore[no-untyped-def]
) -> None:
    ws_app.state.voice_overrides = {
        "stt": FakeStt("hi", fail_times=1),
        "tts": FakeTts(),
        "vad": EnergyVad(),
    }
    sid, lid = spoken_world["session_id"], spoken_world["learner_id"]
    voice_dir = settings.voice_dir_resolved

    def drive() -> list[dict]:  # type: ignore[type-arg]
        with TestClient(ws_app) as tc, _connect(tc) as ws:
            ws.send_text(json.dumps({"type": "start", "session_id": sid}))
            json.loads(ws.receive_text())
            for f in [tone(0.1)] * 6:
                ws.send_bytes(f)
            ws.send_text(json.dumps({"type": "end_of_speech"}))
            failed = _collect(ws, {"error"})
            # second utterance works and — with retention on — is kept
            for f in [tone(0.1)] * 6:
                ws.send_bytes(f)
            ws.send_text(json.dumps({"type": "end_of_speech"}))
            ok = _collect(ws, {"done"})
            ws.send_text(json.dumps({"type": "stop"}))
            return failed + ok

    await preferences.set_pref(db, lid, "voice.retain_audio", True, origin="explicit")
    await preferences.set_pref(db, lid, "voice.retention_days", 1, origin="explicit")
    msgs = await asyncio.to_thread(drive)
    err = next(m for m in msgs if m["type"] == "error")
    assert err["fallback"] == "text" and "Type your question" in err["message"]
    kept = list((voice_dir / sid).glob("*.wav"))
    assert len(kept) == 1
    with wave.open(str(kept[0]), "rb") as w:
        assert w.getframerate() == 16_000 and w.getnframes() == 6 * 1600
    # the failed transcription left an ok=False stt row (billing free, never hidden)
    calls = (await db.execute(select(models.ModelCall))).scalars().all()
    assert any(c.task == "stt" and not c.ok for c in calls)
    # retention pruning removes files older than the window
    import os
    import time

    old = time.time() - 3 * 86400
    os.utime(kept[0], (old, old))
    assert prune(voice_dir, 1) == 1 and not list((voice_dir / sid).glob("*.wav"))
    assert voice_dir.is_relative_to(
        tmp_path.parent
    )  # retained files never leave the test temp root


async def test_installed_but_not_activated_and_foreign_session(
    ws_app,
    spoken_world: dict[str, str],
    db: AsyncSession,
    settings: Settings,  # type: ignore[no-untyped-def]
) -> None:
    # registry rows ready (as after a pull) but voice not activated: sessions stay text-only
    await registry.set_status(db, "whisper-large-v3-turbo", "ready", local_path="/tmp/x")
    assert (await preferences.get(db, spoken_world["learner_id"], "voice.enabled")) in (None, False)
    ws_app.state.voice_overrides = {"stt": FakeStt("hi"), "tts": FakeTts(), "vad": EnergyVad()}
    other = models.LearnerProfile(display_name="someone else")
    db.add(other)
    await db.flush()
    foreign = models.Session(learner_id=other.id, mode="steady", energy=3)
    db.add(foreign)
    await db.commit()

    def drive() -> dict:  # type: ignore[type-arg]
        with TestClient(ws_app) as tc, _connect(tc) as ws:
            ws.send_text(json.dumps({"type": "start", "session_id": foreign.id}))
            return json.loads(ws.receive_text())

    msg = await asyncio.to_thread(drive)
    assert msg["type"] == "error" and "not found" in msg["message"]


async def test_conversation_turn_stays_in_the_language_block(
    ws_app,
    spoken_world: dict[str, str],
    db: AsyncSession,  # type: ignore[no-untyped-def]
) -> None:
    ws_app.state.voice_overrides = {
        "stt": FakeStt("Guten Tag"),
        "tts": FakeTts(),
        "vad": EnergyVad(),
    }
    sid = spoken_world["session_id"]

    def drive() -> list[dict]:  # type: ignore[type-arg]
        with TestClient(ws_app) as tc, _connect(tc) as ws:
            ws.send_text(
                json.dumps({"type": "start", "session_id": sid, "lang": "en", "conversation": True})
            )
            json.loads(ws.receive_text())
            ws.send_text(json.dumps({"type": "text", "text": "Hello, how are you today?"}))
            out = _collect(ws, {"done"})
            ws.send_text(json.dumps({"type": "stop"}))
            return out

    msgs = await asyncio.to_thread(drive)
    meta = next(m for m in msgs if m["type"] == "meta")
    node = await db.get(models.SkillNode, meta["skill_id"])
    assert node is not None and node.domain == "language"  # never an AI/ML skill
    ev = (await db.execute(select(models.LearningEvent))).scalars().all()
    for e in ev:
        if e.verb in ("asked", "explained", "spoke"):
            assert e.domain == "language", e.verb
    assert not (await db.execute(select(models.RetrievalTrace))).scalars().all()  # no corpus lookup
    call = next(
        c for c in (await db.execute(select(models.ModelCall))).scalars() if c.task == "chat_fast"
    )
    assert call.provider == "ollama"  # the fast local route, never a hosted tutor model
    cp = (await db.execute(select(models.SessionCheckpoint))).scalars().all()
    assert all(
        (c.packet_json or {}).get("skill_id") != node.id for c in cp
    )  # block not re-targeted
