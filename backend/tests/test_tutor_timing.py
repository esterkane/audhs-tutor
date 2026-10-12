import asyncio
import json
import logging

import pytest

from app.core import tutor_timing as timing


@pytest.mark.asyncio
async def test_elapsed_marks_cover_transport_without_content(caplog, monkeypatch):
    clock = [10.0]
    monkeypatch.setattr(timing.time, "perf_counter", lambda: clock[0])
    messages = []

    async def app(scope, receive, send):
        clock[0] = 11.0
        timing.mark("dependencies_ready")
        await send({"type": "http.response.start", "status": 200, "headers": []})
        clock[0] = 12.0
        timing.mark("first_text_ready")
        clock[0] = 13.0
        timing.mark("first_text_ready")
        await send({"type": "http.response.body", "body": b"private answer", "more_body": True})
        clock[0] = 14.0
        await send({"type": "http.response.body", "body": b"", "more_body": False})
        clock[0] = 20.0  # background work must not inflate body completion

    async def send(message):
        messages.append(message)

    async def receive():
        return {"type": "http.request", "body": b"private question"}

    with caplog.at_level(logging.INFO, logger="uvicorn.error.tutor_timing"):
        await timing.TutorTimingMiddleware(app)(
            {"type": "http", "path": "/api/tutor/stream"}, receive, send
        )
    record = json.loads(caplog.records[-1].getMessage().removeprefix("tutor_timing "))
    assert record["marks_ms"] == {
        "dependencies_ready": 1000,
        "headers_sent": 1000,
        "first_text_ready": 2000,
        "body_sent": 4000,
    }
    assert record["body_completed"] is True
    assert "private" not in caplog.text
    assert messages[1]["body"] == b"private answer"
    assert timing._current.get() is None


@pytest.mark.asyncio
async def test_cancellation_logs_incomplete_and_restores_context(caplog):
    async def app(scope, receive, send):
        timing.mark("turn_started")
        raise asyncio.CancelledError

    async def transport(*args):
        raise AssertionError("No transport expected")

    with caplog.at_level(logging.INFO, logger="uvicorn.error.tutor_timing"):
        with pytest.raises(asyncio.CancelledError):
            await timing.TutorTimingMiddleware(app)(
                {"type": "http", "path": "/api/tutor/stream"}, transport, transport
            )
    record = json.loads(caplog.records[-1].getMessage().removeprefix("tutor_timing "))
    assert record["body_completed"] is False
    assert "first_text_ready" not in record["marks_ms"]
    assert timing._current.get() is None
