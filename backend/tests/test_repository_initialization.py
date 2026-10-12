import asyncio
from types import SimpleNamespace

import pytest
from starlette.applications import Starlette

from app.api.deps import get_repo
from app.core.config import Settings


@pytest.mark.asyncio
async def test_concurrent_requests_build_one_repository(monkeypatch):
    app = Starlette()
    request = SimpleNamespace(app=app)
    entered = asyncio.Event()
    release = asyncio.Event()
    calls = []
    repo = object()

    async def build(db, settings):
        calls.append(db)
        entered.set()
        await release.wait()
        return repo

    monkeypatch.setattr("app.knowledge.reindex.build_repo", build)
    first = asyncio.create_task(get_repo(request, object(), Settings()))
    await entered.wait()
    second = asyncio.create_task(get_repo(request, object(), Settings()))
    await asyncio.sleep(0)
    release.set()
    assert await first is repo
    assert await second is repo
    assert len(calls) == 1


@pytest.mark.asyncio
@pytest.mark.parametrize("cancel", [False, True])
async def test_failed_or_cancelled_builder_releases_waiter(monkeypatch, cancel):
    from app.api.deps import shared_repo

    app = Starlette()
    entered = asyncio.Event()
    release = asyncio.Event()
    calls = 0
    repo = object()

    async def build(db, settings):
        nonlocal calls
        calls += 1
        if calls == 1:
            entered.set()
            await release.wait()
            raise RuntimeError("temporary initialization failure")
        return repo

    monkeypatch.setattr("app.knowledge.reindex.build_repo", build)
    first = asyncio.create_task(shared_repo(app, object(), Settings()))
    await entered.wait()
    second = asyncio.create_task(get_repo(SimpleNamespace(app=app), object(), Settings()))
    await asyncio.sleep(0)
    if cancel:
        first.cancel()
    else:
        release.set()
    with pytest.raises(asyncio.CancelledError if cancel else RuntimeError):
        await first
    assert await asyncio.wait_for(second, 1) is repo
    assert app.state.repo is repo
    assert calls == 2


@pytest.mark.asyncio
async def test_voice_factory_and_http_share_ready_repository():
    from app.api.deps import shared_repo

    app = Starlette()
    calls = []
    repo = object()

    def factory():
        calls.append(1)
        return repo

    app.state.repo_factory = factory
    assert await shared_repo(app, object(), Settings()) is repo
    assert await get_repo(SimpleNamespace(app=app), object(), Settings()) is repo
    assert calls == [1]
