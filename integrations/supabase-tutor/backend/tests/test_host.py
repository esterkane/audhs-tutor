"""Host mode (T3.1, AuDHS ADR 0021 draft): host identity, before_turn / on_model_call hooks, explicit delivery."""
from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any
from urllib.parse import urlparse, urlunparse
from uuid import UUID, uuid4

import httpx
import psycopg
import pytest
from fastapi import FastAPI
from psycopg_pool import AsyncConnectionPool

from backend.tests.test_orchestrator import FakeClient, FakeRetriever, FakeStream, message, text_reply
from backend.tests.test_router import parse_sse
from backend.tutor.host import HostRefusal, HostVerifier, ModelCall
from backend.tutor.lab_runner import lab_pool
from backend.tutor.ledger import PgLedger
from backend.tutor.prompt import SessionState, turn_system_text
from backend.tutor.service import TutorService
from kaenguru_tutor import router


class Hooks:
    def __init__(self) -> None:
        self.refuse: str | None = None
        self.calls: list[tuple[UUID, ModelCall]] = []

    async def before_turn(self, user_id: UUID) -> None:
        if self.refuse:
            raise HostRefusal(self.refuse, 503)

    async def on_model_call(self, user_id: UUID, call: ModelCall) -> None:
        self.calls.append((user_id, call))


@pytest.fixture
async def host(db_url: str) -> AsyncIterator[tuple[httpx.AsyncClient, Hooks, FakeClient, UUID]]:
    user = uuid4()
    lab_url = urlunparse(urlparse(db_url)._replace(path="/lab"))
    app_pool = AsyncConnectionPool(db_url, min_size=1, max_size=4, open=False)
    fake, hooks = FakeClient([]), Hooks()
    svc = TutorService(app_pool=app_pool, lab_pool=lab_pool(lab_url, min_size=1, max_size=2), lab_url=lab_url,
                       verifier=HostVerifier(user), retriever=FakeRetriever(), ledger=PgLedger(app_pool),
                       anthropic=fake, hooks=hooks)  # type: ignore[arg-type]
    await svc.open()
    app = FastAPI()
    app.include_router(router, prefix="/api/kaenguru")
    app.state.tutor = svc
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://host") as client:
        yield client, hooks, fake, user
    await svc.close()
    with psycopg.connect(db_url, autocommit=True) as conn:
        conn.execute("delete from tutor.session where user_id = %s", (user,))


async def test_host_identity_needs_no_token_and_rls_still_applies(host: Any, db_url: str) -> None:
    client, _, _, user = host
    created = await client.post("/api/kaenguru/session", json={"delivery": "explicit"})
    assert created.status_code == 201 and created.json()["delivery"] == "explicit"
    with psycopg.connect(db_url) as conn:  # written as the host learner's Supabase user
        owner = conn.execute("select user_id from tutor.session where id = %s", (created.json()["id"],)).fetchone()
    assert owner and owner[0] == user


async def test_before_turn_can_refuse_and_every_model_call_is_reported(host: Any) -> None:
    client, hooks, fake, user = host
    sid = (await client.post("/api/kaenguru/session", json={})).json()["id"]
    hooks.refuse = "daily hosted budget spent"
    refused = await client.post("/api/kaenguru/turn", json={"session_id": sid, "text": "Hallo"})
    assert (refused.status_code, refused.json()["detail"]) == (503, "daily hosted budget spent")
    assert fake.requests == [] and hooks.calls == []

    hooks.refuse = None
    fake.script += [FakeStream([], message([{"type": "tool_use", "id": "toolu_1", "name": "search_docs",
                                             "input": {"query": "42501 grant"}}], stop="tool_use")),
                    text_reply("Gut, dann schauen wir auf die Evidenz.")]
    events = parse_sse((await client.post("/api/kaenguru/turn", json={"session_id": sid, "text": "Hallo"})).text)
    assert events[-1][0] in ("turn", "incident")
    assert [u for u, _ in hooks.calls] == [user, user]  # one report per API call: tool call + final answer
    assert all(c.model == "claude-sonnet-5-5" and c.usage["input_tokens"] == 100 and c.ms >= 0 for _, c in hooks.calls)


def test_explicit_delivery_adds_its_block_only_when_chosen() -> None:
    explicit = turn_system_text(SessionState(delivery="explicit"))
    assert "# DELIVERY: explicit" in explicit and "at most one application check when useful" in explicit
    assert "DELIVERY" not in turn_system_text(SessionState())


async def test_midstream_host_refusal_emits_error_without_saving_partial_turn() -> None:
    import asyncio
    from types import SimpleNamespace
    from unittest.mock import AsyncMock

    from backend.tutor.orchestrator import Token
    from backend.tutor.router import TurnRequest, turn

    async def failed_turn(**kwargs):
        yield Token("Partial answer")
        raise HostRefusal("Shared hosted budget cannot cover the next call", 503)

    previous = [{"role": "user", "content": "Previous question"}]
    store = SimpleNamespace(session=AsyncMock(return_value={"mode": "lesson"}),
                            history=AsyncMock(return_value=previous), append=AsyncMock())
    lock = asyncio.Lock()
    svc = SimpleNamespace(anthropic=object(), hooks=None, store=store, lock=lambda _: lock,
                          session_state=AsyncMock(return_value=SessionState()),
                          runner=lambda _: SimpleNamespace(active=None), retriever=None,
                          ledger=None, web=None,
                          orchestrator=lambda _: SimpleNamespace(run_turn=failed_turn))
    response = await turn(TurnRequest(session_id=uuid4(), text="Next question"), svc, uuid4())
    events = [event async for event in response.body_iterator]
    assert [event["event"] for event in events] == ["token", "error"]
    import json
    assert json.loads(events[-1]["data"]) == {
        "status": 503, "message": "Shared hosted budget cannot cover the next call"}
    store.append.assert_not_awaited()
    assert previous == [{"role": "user", "content": "Previous question"}]
    assert not lock.locked()
