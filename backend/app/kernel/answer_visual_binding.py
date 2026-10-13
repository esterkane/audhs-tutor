"""Read-only private Ask snapshots. No inference, acceptance or learning-state writes.

A read result is not durable: future save/review transactions must resolve again.
Currency is not accuracy or transmission permission. All snapshots remain private.
"""

import hashlib
import json
from dataclasses import dataclass
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import answer_sources
from app.db.models import Chunk, DocumentVersion, TutorAnswer
from app.schemas.answer_visual_binding import AnswerVisualBinding
from app.schemas.answers import SavedSourceCheck

MAX_ANSWERS = 32
MAX_SNAPSHOT_BYTES = 2 * 1024 * 1024


def _json(value: Any) -> str:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False
    )


def _hash(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class AnswerVisualResolution:
    binding: AnswerVisualBinding
    # Immutable serialized private snapshot, including original generation inputs.
    snapshot_json: str
    issues: tuple[str, ...]
    source_checks: dict[str, SavedSourceCheck]

    @property
    def grounding(self) -> str:
        if self.issues or any(
            check.omitted or any(source.status != "unchanged" for source in check.sources)
            for check in self.source_checks.values()
        ):
            return "unknown"
        return (
            "sources_recorded"
            if any(check.sources for check in self.source_checks.values())
            else "ungrounded"
        )


def _references(row: TutorAnswer, issues: set[str]) -> list[str]:
    meta = row.metadata_json
    parent = meta.get("parent_answer_id")
    ids = meta.get("context_answer_ids")
    snapshots = meta.get("context_snapshots")
    hashes = meta.get("context_answer_hashes")
    if not isinstance(ids, list) or not all(isinstance(i, str) and i for i in ids):
        issues.add("incomplete_lineage")
        ids = []
    if (
        not isinstance(snapshots, list)
        or not all(isinstance(s, dict) for s in snapshots)
        or [s.get("answer_id") for s in snapshots] != ids
        or not isinstance(hashes, dict)
        or set(hashes) != set(ids)
        or len(set(ids)) != len(ids)
        or meta.get("history_turns") != len(ids)
    ):
        issues.add("incomplete_lineage")
    if "parent_answer_id" not in meta or parent != row.request_json.get("parent_answer_id"):
        issues.add("incomplete_lineage")
    if parent is not None and (not isinstance(parent, str) or not parent):
        issues.add("incomplete_lineage")
        parent = None
    if (parent and (not ids or ids[0] != parent)) or (not parent and ids):
        issues.add("incomplete_lineage")
    if not isinstance(meta.get("sources"), list) or not isinstance(
        meta.get("source_text_hashes"), dict
    ):
        issues.add("incomplete_sources")
    elif any(
        not isinstance(source, dict) or not isinstance(source.get("chunk_id"), str)
        for source in meta["sources"]
    ):
        issues.add("incomplete_sources")
    else:
        sources = meta["sources"]
        hashes = meta["source_text_hashes"]
        source_ids = [source["chunk_id"] for source in sources]
        if len(set(source_ids)) != len(source_ids) or set(source_ids) != set(hashes):
            issues.add("incomplete_sources")
        selection = row.request_json.get("sources")
        if selection is None:
            if sources or hashes:
                issues.add("incomplete_sources")
        elif (
            not isinstance(selection, dict)
            or selection.get("passage_ids") != source_ids
            or selection.get("passage_hashes") != hashes
        ):
            issues.add("incomplete_sources")
        for source in sources:
            text = source.get("text")
            if (
                not isinstance(text, str)
                or _hash(text) != source.get("text_hash")
                or source.get("text_hash") != hashes.get(source["chunk_id"])
                or not source.get("document_version_id")
            ):
                issues.add("incomplete_sources")
    if not meta.get("model") or not meta.get("prompt_version"):
        issues.add("missing_generation_identity")
    return list(dict.fromkeys(([parent] if parent else []) + ids))


def _check_history(rows: dict[str, TutorAnswer], issues: set[str]) -> None:
    for row in rows.values():
        snapshots = row.metadata_json.get("context_snapshots")
        if not isinstance(snapshots, list):
            continue
        hashes = row.metadata_json.get("context_answer_hashes")
        hashes = hashes if isinstance(hashes, dict) else {}
        for snapshot in snapshots:
            if not isinstance(snapshot, dict):
                continue
            identity = snapshot.get("answer_id")
            ancestor = rows.get(identity) if isinstance(identity, str) else None
            if ancestor is None:
                issues.add("unavailable_ancestor")
                continue
            expected = {
                "answer_id": ancestor.id,
                "answer_hash": _hash(ancestor.text),
                "question": ancestor.request_json.get("question"),
                "text": ancestor.text,
                "sources": ancestor.metadata_json.get("sources", []),
                "source_text_hashes": ancestor.metadata_json.get("source_text_hashes", {}),
                "origin_status": ancestor.metadata_json.get("origin_status", "unknown"),
            }
            if snapshot != expected or hashes.get(identity) != expected["answer_hash"]:
                issues.add("changed_ancestor")


async def resolve_answer_binding(
    db: AsyncSession, learner_id: str, answer_id: str, *, learning_purpose: str | None = None
) -> AnswerVisualResolution:
    """Resolve owned Ask records without flushing or trusting the ORM identity map.

    All ancestors are traversed, not merely the three turns in the last prompt.
    Limits/malformed/legacy records are explicit unknowns, never owner-authorship.
    Missing and foreign root IDs have the same error. Foreign ancestor text is not read.
    """
    rows: dict[str, TutorAnswer] = {}
    records: list[dict[str, Any]] = []
    issues: set[str] = set()
    pending: list[tuple[str, tuple[str, ...]]] = [(answer_id, ())]
    visited: set[str] = set()
    total = 0
    with db.no_autoflush:
        while pending:
            identity, path = pending.pop()
            if identity in path:
                issues.add("cyclic_lineage")
                continue
            if identity in visited:
                continue
            if len(visited) >= MAX_ANSWERS:
                issues.add("lineage_limit")
                break
            visited.add(identity)
            stored = (
                (
                    await db.execute(
                        select(
                            TutorAnswer.id,
                            TutorAnswer.learner_id,
                            TutorAnswer.surface,
                            TutorAnswer.request_json,
                            TutorAnswer.text,
                            TutorAnswer.metadata_json,
                            TutorAnswer.created_at,
                        ).where(TutorAnswer.id == identity, TutorAnswer.learner_id == learner_id)
                    )
                )
                .mappings()
                .one_or_none()
            )
            if stored is None or stored["surface"] != "ask":
                if identity == answer_id:
                    raise KeyError("Ask answer unavailable")
                issues.add("unavailable_ancestor")
                continue
            row = TutorAnswer(**stored)
            if not isinstance(row.request_json.get("question"), str):
                raise ValueError("Ask question unavailable")
            record = dict(stored)
            record["created_at"] = row.created_at
            total += len(_json(record).encode("utf-8"))
            if total > MAX_SNAPSHOT_BYTES:
                raise ValueError("Answer lineage snapshot exceeds size limit")
            rows[identity] = row
            records.append(record)
            references = _references(row, issues)
            # Depth-first traversal makes cycle detection independent of shared parents.
            pending.extend((ref, (*path, identity)) for ref in reversed(references))
        _check_history(rows, issues)
        checks = await answer_sources.check_many(db, learner_id, list(rows.values()))
        # Text currency alone cannot detect reassignment to another source version.
        ids = [source.chunk_id for check in checks.values() for source in check.sources]
        versions = {
            record.id: (record.document_version_id, record.document_id)
            for record in await db.execute(
                select(Chunk.id, Chunk.document_version_id, DocumentVersion.document_id)
                .join(DocumentVersion, DocumentVersion.id == Chunk.document_version_id)
                .where(Chunk.id.in_(ids))
            )
        }
        for row in rows.values():
            raw_sources = row.metadata_json.get("sources")
            if not isinstance(raw_sources, list):
                continue
            saved_sources = {
                s["chunk_id"]: s
                for s in raw_sources
                if isinstance(s, dict) and isinstance(s.get("chunk_id"), str)
            }
            for source in checks[row.id].sources:
                saved_source = saved_sources.get(source.chunk_id)
                current_version = versions.get(source.chunk_id)
                if (
                    saved_source
                    and current_version
                    and (
                        saved_source.get("document_version_id") != current_version[0]
                        or (
                            saved_source.get("document_id") is not None
                            and saved_source["document_id"] != current_version[1]
                        )
                    )
                ):
                    source.status = "changed"
    snapshot = _json({"answers": sorted(records, key=lambda r: r["id"]), "issues": sorted(issues)})
    root = rows[answer_id]
    binding = AnswerVisualBinding(
        answer_id=answer_id,
        question_sha256=_hash(root.request_json["question"]),
        answer_sha256=_hash(root.text),
        lineage_sha256=_hash(snapshot),
        learning_purpose=learning_purpose,
    )
    return AnswerVisualResolution(binding, snapshot, tuple(sorted(issues)), checks)


async def validate_answer_binding(
    db: AsyncSession, learner_id: str, binding: AnswerVisualBinding
) -> AnswerVisualResolution:
    """Reject changed target/lineage; return currency issues separately for future UI.

    This alone must never be treated as permission to accept, export or transmit.
    """
    current = await resolve_answer_binding(
        db, learner_id, binding.answer_id, learning_purpose=binding.learning_purpose
    )
    if current.binding != binding:
        raise ValueError("Ask answer or lineage changed")
    return current
