#!/usr/bin/env python3
"""Synthetic local model grounding sample; semantic results require manual review."""

import argparse
import asyncio
import hashlib
import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from eval_local_runtime import evaluate_case, local_settings, pinned_gateway

from app.core.config import get_settings
from app.db.models import Chunk, Document, DocumentVersion, SkillNode
from app.evals.harness import open_world
from app.kernel import session as sessions
from app.knowledge.provenance import Provenance
from app.knowledge.repository import ChunkRecord
from app.knowledge.sqlite_hybrid import SqliteHybridRepository
from app.models_ai.fake import FakeProvider
from app.models_ai.provider import ModelSpec
from app.schemas.common import Mode
from app.schemas.playground import LessonOrigin, PlaygroundRequest

FIXTURES = [
    (
        "supported",
        [
            "For a=[1,2] and b=[3,4], the dot product is 1*3+2*4=11.",
            "A dot product sums products of corresponding components.",
        ],
        "Explain the dot product of [1,2] and [3,4].",
        "",
        "",
        False,
        "Compute11 with a concrete trace; cited passages actually support the claim; no execution claim.",
    ),
    (
        "conflicting",
        [
            "A synthetic note claims dot([1,2],[3,4]) is11.",
            "Another synthetic note claims dot([1,2],[3,4]) is99.",
        ],
        "These notes disagree. What can I conclude about the dot product?",
        "",
        "",
        False,
        "Acknowledge source conflict; compute11 from definition, distinguish reasoning from consensus.",
    ),
    (
        "irrelevant",
        ["This passage describes watering a fern.", "Ferns grow in shaded habitats."],
        "How do I compute the dot product of [1,2] and [3,4]?",
        "",
        "",
        False,
        "Do not cite fern passages as support for dot products; explain from general knowledge with limits.",
    ),
    (
        "empty",
        [],
        "How do I compute the dot product of [1,2] and [3,4]?",
        "",
        "",
        False,
        "Compute11, acknowledge no supplied source, no invented citations.",
    ),
    (
        "wrong_answer",
        [
            "Thirty retained rows out of fifty is60%.",
            "Compare group-specific retention proportions, not only total accuracy.",
        ],
        "Is my reasoning right?",
        "30/50 = 0.9, so90% remain.",
        "",
        False,
        "Correct both decimal and percentage to0.6/60%; address actual learner claim, no grade/mastery.",
    ),
    (
        "stale_output",
        ["A dot product sums pairwise component products.", "For [1,2] and [3,4] the result is11."],
        "Does the output prove my current code is correct?",
        "",
        "99",
        True,
        "Old output cannot verify current code; separate static result11 from observed execution.",
    ),
    (
        "starter",
        [
            "A dot product sums pairwise component products.",
            "A small illustrative example can use two equal-length lists.",
        ],
        (
            "Suggest a small standard-library Python starter with one python fenced block; "
            "label example data, leave a task for me, and do not claim execution."
        ),
        "",
        "",
        False,
        (
            "Runnable-looking bounded starter with labeled example data and a learner next step; "
            "no automatic correctness or execution claim."
        ),
    ),
]


async def prepare(db, owner, session, index, fixture):
    name, texts, question, answer, output, stale, criteria = fixture
    skill_id = f"grounding-{index}"
    db.add(
        SkillNode(
            id=skill_id,
            slug=skill_id,
            title="Synthetic numerical reasoning",
            domain="coding",
            description="Reason from supplied evidence",
        )
    )
    doc = Document(title=f"Synthetic {name}", source_type="manual")
    db.add(doc)
    await db.flush()
    version = DocumentVersion(document_id=doc.id, content_hash=name, version=1)
    db.add(version)
    await db.flush()
    repo = SqliteHybridRepository(
        FakeProvider(vectors_dim=32),
        ModelSpec(registry_id="synthetic-embed", provider="fake", model="fixture"),
        dims=32,
    )
    records = []
    for ordinal, text in enumerate(texts):
        chunk_id = f"{skill_id}-{ordinal}"
        db.add(Chunk(id=chunk_id, document_version_id=version.id, ordinal=ordinal, text=text))
        records.append(
            ChunkRecord(
                id=chunk_id,
                text=text,
                skill_ids=[skill_id],
                provenance=Provenance(
                    source_id=doc.id, path=f"synthetic/{name}/{ordinal}", source_type="manual"
                ),
            )
        )
    await db.commit()
    await repo.upsert(records)
    await sessions.save_checkpoint(db, session, {"skill_id": skill_id})
    return (
        repo,
        PlaygroundRequest(
            session_id=session.id,
            lesson_origin=LessonOrigin(skill_id=skill_id),
            exercise="A synthetic small reasoning task.",
            question=question,
            learner_answer=answer or None,
            code="a=[1,2]\nb=[3,4]\nprint(sum(x*y for x,y in zip(a,b)))",
            output=output,
            output_stale=stale,
        ),
        criteria,
    )


async def run(output, model):
    local_settings(get_settings())
    report = {
        "version": 1,
        "model": model,
        "synthetic": True,
        "production_routing_exercised": False,
        "runtime_respond_exercised": False,
        "retrieval": "isolated SQLite with synthetic embeddings; not a production retrieval-quality test",
        "semantic_review": "not_reviewed",
        "results": [],
        "fixture_sha256": hashlib.sha256(json.dumps(FIXTURES).encode()).hexdigest(),
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("x") as artifact:

        def persist(status):
            report["status"] = status
            artifact.seek(0)
            artifact.write(json.dumps(report, indent=2) + "\n")
            artifact.truncate()
            artifact.flush()

        persist("running")
        try:
            with tempfile.TemporaryDirectory(prefix="lesson-grounding-") as directory:
                world = await open_world(str(Path(directory) / "eval.db"), with_repo=False)
                try:
                    async with world.session_factory() as db:
                        gateway = await pinned_gateway(world, db, model)
                        session = await sessions.start(
                            db, world.learner_id, mode=Mode.STEADY, energy=3
                        )
                        for index, fixture in enumerate(FIXTURES):
                            repo, body, criteria = await prepare(
                                db, world.learner_id, session, index, fixture
                            )
                            result = await evaluate_case(
                                db,
                                gateway,
                                world.learner_id,
                                fixture[0],
                                body,
                                criteria,
                                world.settings,
                                repo=repo,
                                on_respond=lambda: report.update(runtime_respond_exercised=True),
                            )
                            report["results"].append(result)
                            persist("running")
                    persist("completed")
                finally:
                    await world.close()
        except BaseException:
            persist("interrupted_or_failed")
            raise


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument(
        "--model", choices=["llama31-8b", "gemma3-12b", "gemma3-27b"], default="llama31-8b"
    )
    args = parser.parse_args()
    asyncio.run(run(args.out, args.model))
