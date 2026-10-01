"""Async engine/session factory. No module-level singletons: the app keeps them on app.state."""

import sqlite3
from collections.abc import AsyncIterator
from typing import Any

from fastapi import Request
from sqlalchemy import event
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

SQLITE_PRAGMAS = (
    "PRAGMA journal_mode=WAL",
    "PRAGMA foreign_keys=ON",
    "PRAGMA synchronous=NORMAL",
    "PRAGMA busy_timeout=5000",
)


def _apply_pragmas(dbapi_connection: Any, _: Any) -> None:
    cur = dbapi_connection.cursor()
    for pragma in SQLITE_PRAGMAS:
        cur.execute(pragma)
    cur.close()


def make_engine(url: str) -> AsyncEngine:
    engine = create_async_engine(url, connect_args={"timeout": 30})
    if url.startswith("sqlite"):
        event.listen(engine.sync_engine, "connect", _apply_pragmas)
    return engine


def make_session_factory(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(engine, expire_on_commit=False)


async def get_db(request: Request) -> AsyncIterator[AsyncSession]:
    factory: async_sessionmaker[AsyncSession] = request.app.state.session_factory
    async with factory() as session:
        yield session


def sync_connect(sync_url: str) -> sqlite3.Connection:
    """Plain sqlite3 connection for scripts (export/wipe) — same pragmas."""
    path = sync_url.removeprefix("sqlite:///")
    conn = sqlite3.connect(path)
    for pragma in SQLITE_PRAGMAS:
        conn.execute(pragma)
    return conn
