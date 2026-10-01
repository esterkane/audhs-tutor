"""A timed-out prior voice task must keep exclusive ownership of its DB session."""

import json
from unittest.mock import AsyncMock, Mock

import pytest

from app.voice.loop import VoiceLoop, VoiceState


@pytest.mark.parametrize(
    "message", [{"type": "text", "text": "next"}, {"type": "start", "session_id": "other"}]
)
async def test_busy_turn_blocks_text_and_restart(message):
    loop = VoiceLoop(
        Mock(), Mock(), stt=None, tts=None, vad=Mock(), voice_dir=Mock(), learner_id="owner"
    )
    state = VoiceState(
        session_id="original",
        skill_id=None,
        lang=None,
        text_only=True,
        conversation=False,
        voice="",
        early_speech=False,
    )
    loop._start = AsyncMock(return_value=state)
    loop._respond = AsyncMock()
    prior = Mock()
    loop._turn_task = prior

    async def still_running():
        loop._busy_beyond_interrupt = True

    loop._interrupt = AsyncMock(side_effect=still_running)
    ws = Mock()
    ws.receive = AsyncMock(
        side_effect=[
            {
                "type": "websocket.receive",
                "text": json.dumps({"type": "start", "session_id": "original"}),
            },
            {"type": "websocket.receive", "text": json.dumps(message)},
            {"type": "websocket.disconnect"},
        ]
    )
    ws.send_text = AsyncMock()
    await loop.serve(ws)
    assert loop._turn_task is prior
    loop._respond.assert_not_called()
    loop._start.assert_awaited_once()
    sent = [json.loads(call.args[0]) for call in ws.send_text.await_args_list]
    assert sent == [
        {
            "type": "error",
            "message": (
                "The previous voice response is still finishing. "
                "This new request was not started or queued. Wait, then send it again."
            ),
            "fallback": "text",
        }
    ]


async def test_wait_previous_allows_work_only_after_cleanup_finishes():
    loop = VoiceLoop(
        Mock(), Mock(), stt=None, tts=None, vad=Mock(), voice_dir=Mock(), learner_id="owner"
    )
    ws = Mock()
    ws.send_text = AsyncMock()
    loop._busy_beyond_interrupt = True
    loop._interrupt = AsyncMock()
    assert not await loop._wait_previous(ws)
    loop._busy_beyond_interrupt = False
    assert await loop._wait_previous(ws)
    assert ws.send_text.await_count == 1
