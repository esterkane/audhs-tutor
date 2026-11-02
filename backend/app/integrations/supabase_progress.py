"""Neutral discussion cannot manufacture assessed progress, regardless of model provider."""

from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from functools import lru_cache, wraps
from typing import Any, cast, get_args

from pydantic import BaseModel, Field, create_model

from app.core.errors import AppError

_NEUTRAL: ContextVar[bool] = ContextVar("supabase_neutral_progress", default=False)


def install_progress_guard() -> None:
    from app.integrations.supabase_project import project_module

    project_module()
    from backend.tutor.tools import HANDLERS, ToolResult

    model, original = HANDLERS["ledger_update"]
    if getattr(original, "_audhs_progress_guard", False):
        return

    @wraps(original)
    async def guarded(args: Any, ctx: Any, budget: Any) -> Any:
        if _NEUTRAL.get():
            return ToolResult(
                "Neutral discussion does not assess knowledge or update mastery. "
                "Continue the explanation without claiming a progress update.",
                is_error=True,
            )
        return await original(args, ctx, budget)

    guarded.__dict__["_audhs_progress_guard"] = True
    HANDLERS["ledger_update"] = model, guarded


@contextmanager
def progress_scope(state: Any) -> Iterator[None]:
    install_progress_guard()
    token = _NEUTRAL.set(getattr(state, "mode", None) == "neutral")
    try:
        yield
    finally:
        _NEUTRAL.reset(token)


def neutral_progress() -> bool:
    return _NEUTRAL.get()


def progress_tools(tools: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if not neutral_progress():
        return tools
    return [tool for tool in tools if tool.get("name") != "ledger_update"]


@lru_cache
def _neutral_schema(base: type[BaseModel]) -> type[BaseModel]:
    metadata_types = [
        kind
        for kind in get_args(base.model_fields["state"].annotation)
        if isinstance(kind, type) and issubclass(kind, BaseModel)
    ]
    if len(metadata_types) != 1:
        return base  # Required documentation-search replies have no final metadata.
    metadata = create_model(
        "UnassessedProjectMetadata",
        __base__=metadata_types[0],
        ledger_delta=(list[Any], Field(default_factory=list, max_length=0)),
    )
    return create_model("UnassessedProjectDecision", __base__=base, state=(metadata | None, None))


def progress_schema[ModelT: BaseModel](base: type[ModelT]) -> type[ModelT]:
    return cast(type[ModelT], _neutral_schema(base)) if neutral_progress() else base


def validate_progress(metadata: Any) -> None:
    if not neutral_progress() or metadata is None:
        return
    delta = (
        metadata.get("ledger_delta", [])
        if isinstance(metadata, dict)
        else getattr(metadata, "ledger_delta", [])
    )
    if delta:
        raise AppError(
            "supabase_unassessed_progress", "Discussion cannot change assessed progress.", 422
        )
