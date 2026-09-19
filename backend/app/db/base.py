"""Declarative base + id/time helpers. IDs are ULIDs, timestamps UTC ISO-8601 strings."""

from datetime import UTC, datetime

from sqlalchemy.orm import DeclarativeBase
from ulid import ULID


def new_id() -> str:
    return str(ULID())


def utcnow_iso() -> str:
    return datetime.now(UTC).isoformat(timespec="milliseconds")


class Base(DeclarativeBase):
    pass
