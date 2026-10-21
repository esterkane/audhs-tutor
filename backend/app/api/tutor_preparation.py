"""Optional readiness after HTTP delivery; never part of learning or answer generation."""

import asyncio
import logging
import time

from fastapi import BackgroundTasks, Request

from app.core.config import Settings
from app.db.models import Session
from app.db.traces import ModelCallRecord, write_model_call
from app.kernel import session as ksession
from app.models_ai.ollama import OllamaProvider
from app.models_ai.provider import TaskClass
from app.models_ai.registry import get_spec
from app.models_ai.routing import NoModelReady, Router


def schedule_preparation(
    request: Request,
    background: BackgroundTasks,
    settings: Settings,
    learner_id: str,
    session_id: str,
) -> None:
    provider = getattr(request.app.state, "providers", {}).get("ollama")
    factory = getattr(request.app.state, "session_factory", None)
    if (
        not settings.ollama_prepare_on_session_start
        or not settings.ollama_keep_alive_s
        or not isinstance(provider, OllamaProvider)
        or factory is None
    ):
        return
    # Per-process work set; a second session start cannot queue another load for the
    # same learner while preparation is underway. No durable claim needs recovery.
    pending: set[str] | None = getattr(request.app.state, "tutor_preparation_pending", None)
    if pending is None:
        pending = set()
        request.app.state.tutor_preparation_pending = pending

    async def prepare() -> None:
        # Claim only once the response has actually been delivered. A failed send
        # may never run BackgroundTasks, and must not leave a permanent pending slot.
        if learner_id in pending:
            return
        pending.add(learner_id)
        try:
            async with factory() as db:
                session = await db.get(Session, session_id)
                if not session or session.learner_id != learner_id or session.ended_at:
                    return
                router = Router(settings.routing_profile)
                checkpoint = await ksession.load_checkpoint(db, session.id) or {}
                # Resuming an answer draft should prepare the grader rather than
                # evicting it to load explanation weights. No inference or routing change.
                task = (
                    TaskClass.GRADE_SIMPLE
                    if checkpoint.get("phase") == "assess"
                    else TaskClass.EXPLAIN_SIMPLE
                )
                route = await router.resolve(db, task, learner_id)
                spec = await get_spec(db, route.registry_id)
                if spec.provider != "ollama" or spec.hosted:
                    return
                # Close read transactions before loading weights; no learner writes are pending.
                await db.commit()
                started = time.perf_counter()
                error = None
                loaded = False
                try:
                    async with asyncio.timeout(30):
                        loaded = await provider.preload(spec)
                except Exception as exc:
                    error = type(exc).__name__
                    logging.getLogger(__name__).warning(
                        "Local tutor preparation unavailable: %s", error
                    )
                if loaded or error:
                    await write_model_call(
                        db,
                        ModelCallRecord(
                            provider=spec.provider,
                            model=spec.model,
                            registry_id=spec.registry_id,
                            task="model_preload",
                            route=route.kind,
                            learner_id=learner_id,
                            session_id=session_id,
                            latency_ms=int((time.perf_counter() - started) * 1000),
                            metadata={
                                "operation": "preload",
                                "for_task": str(task),
                            },
                            ok=error is None,
                            outcome="error" if error else "ok",
                            error=error,
                            usage_source="unavailable" if error else "reported",
                            cost_status="free",
                        ),
                    )
        except NoModelReady:
            pass
        except Exception as exc:
            # The response was already delivered. Actual tutor requests retain their usual
            # readiness checks and visible error/recovery paths.
            logging.getLogger(__name__).warning(
                "Local tutor preparation unavailable: %s", type(exc).__name__
            )
        finally:
            pending.discard(learner_id)

    background.add_task(prepare)


def schedule_research_preparation(
    request: Request,
    background: BackgroundTasks,
    settings: Settings,
    learner_id: str,
    draft_id: str,
) -> None:
    """Empty local preload while the learner reads/writes; never generate an answer."""
    from app.db.models import CurriculumDraft

    provider = getattr(request.app.state, "providers", {}).get("ollama")
    factory = getattr(request.app.state, "session_factory", None)
    if (
        not settings.ollama_prepare_on_session_start
        or not settings.ollama_keep_alive_s
        or not isinstance(provider, OllamaProvider)
        or factory is None
    ):
        return
    pending = getattr(request.app.state, "research_preparation_pending", None)
    if pending is None:
        pending = set()
        request.app.state.research_preparation_pending = pending
    ready = getattr(request.app.state, "research_preparation_recent", None)
    if ready is None:
        ready = {}
        request.app.state.research_preparation_recent = ready

    async def prepare() -> None:
        key = None
        claimed = False
        try:
            async with factory() as db:
                draft = await db.get(CurriculumDraft, draft_id)
                if not draft or draft.learner_id != learner_id or draft.status != "draft":
                    return
                route = await Router(settings.routing_profile).resolve(
                    db, TaskClass.EXPLAIN_SIMPLE, learner_id
                )
                spec = await get_spec(db, route.registry_id)
                if spec.provider != "ollama" or spec.hosted:
                    return
                key = (learner_id, spec.model_dump_json())
                if key in pending:
                    return
                if getattr(request.app.state, "research_tutor_active", 0):
                    return
                pending.add(key)
                claimed = True
                await db.commit()
                # Embedding/search may evict weights before this short cooldown expires.
                # Check after claiming so concurrent requests cannot queue duplicate loads.
                if key in ready and time.monotonic() - ready[key] < 180:
                    try:
                        if await provider.is_resident(spec):
                            return
                    except Exception:
                        # Optional readiness remains best-effort; preload still verifies weights.
                        pass
                if getattr(request.app.state, "research_tutor_active", 0):
                    return
                started = time.perf_counter()
                error = None
                loaded = False
                try:
                    async with asyncio.timeout(30):
                        loaded = await provider.preload(spec)
                except Exception as exc:
                    error = type(exc).__name__
                if loaded:
                    ready[key] = time.monotonic()
                if loaded or error:
                    await write_model_call(
                        db,
                        ModelCallRecord(
                            provider=spec.provider,
                            model=spec.model,
                            registry_id=spec.registry_id,
                            task="model_preload",
                            route=route.kind,
                            learner_id=learner_id,
                            latency_ms=int((time.perf_counter() - started) * 1000),
                            metadata={
                                "operation": "preload",
                                "for_task": "research_tutor",
                                "draft_id": draft_id,
                            },
                            ok=error is None,
                            outcome="error" if error else "ok",
                            error=error,
                            usage_source="unavailable" if error else "reported",
                            cost_status="free",
                        ),
                    )
        except Exception as exc:
            logging.getLogger(__name__).warning(
                "Research preparation unavailable: %s", type(exc).__name__
            )
        finally:
            if claimed and key is not None:
                pending.discard(key)

    background.add_task(prepare)
