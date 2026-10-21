import asyncio

import anyio
import pytest

from app.api.sse import sse, with_heartbeats


async def test_heartbeat_does_not_replace_content_or_restart_producer():
    ready = asyncio.Event()
    starts = 0

    async def source():
        nonlocal starts
        starts += 1
        await ready.wait()
        yield sse("token", {"text": "validated reply"})
        yield sse("done", {"text": "validated reply"})

    stream = with_heartbeats(source(), interval_s=0.001)
    assert await anext(stream) == sse("heartbeat", {})
    ready.set()
    assert await anext(stream) == sse("token", {"text": "validated reply"})
    assert await anext(stream) == sse("done", {"text": "validated reply"})
    with pytest.raises(StopAsyncIteration):
        await anext(stream)
    assert starts == 1


async def test_disconnect_scope_joins_cleanup_before_returning():
    started, cleaned = asyncio.Event(), asyncio.Event()

    async def source():
        try:
            started.set()
            await asyncio.Event().wait()
            yield b"never"
        finally:
            await asyncio.sleep(0)  # real async DB/accounting cleanup must be allowed
            cleaned.set()

    async def consume():
        async for _ in with_heartbeats(source()):
            pass

    async with anyio.create_task_group() as group:
        group.start_soon(consume)
        await started.wait()
        group.cancel_scope.cancel()
    assert cleaned.is_set()


async def test_producer_error_is_not_hidden_by_keepalive():
    async def source():
        raise ValueError("failed")
        yield b"never"

    with pytest.raises(ValueError, match="failed"):
        await anext(with_heartbeats(source()))


async def test_cleanup_error_cannot_leave_a_heartbeat_loop_running():
    class Source:
        def __aiter__(self):
            return self

        async def __anext__(self):
            raise StopAsyncIteration

        async def aclose(self):
            raise ValueError("cleanup failed")

    with pytest.raises(ValueError, match="cleanup failed"):
        await anext(with_heartbeats(Source(), interval_s=0.001))
