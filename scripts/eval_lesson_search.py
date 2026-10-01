#!/usr/bin/env python3
"""One synthetic local lesson-search diagnostic; no learning-quality or latency gate."""

import argparse
import asyncio
import hashlib
import json
import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))
from app.db.lesson_answer_memory import retrieve as literal
from app.db.models import Chunk, Document, DocumentVersion, TutorAnswer
from app.evals.harness import open_world
from app.orchestrator.answer_index import populate
from app.orchestrator.lesson_semantic import retrieve


async def run(output: Path) -> None:
    with tempfile.TemporaryDirectory(prefix="lesson-search-") as directory:
        world = await open_world(str(Path(directory) / "eval.db"), with_repo=False)
        try:
            async with world.session_factory() as db:
                doc = Document(title="Synthetic counts", source_type="manual")
                db.add(doc)
                await db.flush()
                version = DocumentVersion(
                    document_id=doc.id, version=1, content_hash="synthetic"
                )
                db.add(version)
                await db.flush()
                text = "Group A retained 90 of 100 rows; group B retained 30 of 50. Retention rates are 90% and 60%."
                chunk = Chunk(
                    id="synthetic-counts",
                    document_version_id=version.id,
                    ordinal=0,
                    text=text,
                )
                db.add(chunk)
                db.add(
                    TutorAnswer(
                        id="synthetic-retention",
                        learner_id=world.learner_id,
                        turn_id="synthetic-retention",
                        surface="tutor",
                        fingerprint="synthetic-retention",
                        text=text,
                        request_json={"text": "How do retention rates differ?"},
                        metadata_json={
                            "skill_id": "synthetic",
                            "teaching_action": "explain",
                            "questioning_style": "explicit",
                            "teaching_contract_key": "synthetic-contract",
                            "sources": [{"chunk_id": chunk.id}],
                            "source_text_hashes": {
                                chunk.id: hashlib.sha256(text.encode()).hexdigest()
                            },
                        },
                    )
                )
                await db.commit()
                indexed = await populate(db, world.settings, world.learner_id)
                args = (
                    world.learner_id,
                    "synthetic",
                    "Compare the proportion remaining in each group",
                    "explain",
                    "explicit",
                    "synthetic-contract",
                )
                direct = await literal(db, *args)
                started = time.perf_counter()
                semantic = await retrieve(db, world.settings, *args)
                result = {
                    "synthetic": True,
                    "scope": "one lookup; excludes generation; not a benchmark",
                    "index": indexed,
                    "literal_ids": [r["answer_id"] for r in direct],
                    "semantic_ids": [r["answer_id"] for r in semantic],
                    "lookup_ms": round((time.perf_counter() - started) * 1000),
                }
                output.parent.mkdir(parents=True, exist_ok=True)
                output.write_text(json.dumps(result, indent=2) + "\n")
                print(json.dumps(result))
        finally:
            await world.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    asyncio.run(run(parser.parse_args().out))
