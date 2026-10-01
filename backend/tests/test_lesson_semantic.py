import hashlib
from pathlib import Path

from app.core.config import Settings
from app.db.answer_vectors import put
from app.db.lesson_answer_memory import retrieve as literal
from app.db.models import Chunk, Document, DocumentVersion, TutorAnswer, TutorAnswerFeedback
from app.kernel.seed import load_seed
from app.models_ai.provider import ModelSpec
from app.models_ai.registry import seed_defaults
from app.orchestrator import answer_semantic, lesson_semantic

SEED = Path(__file__).resolve().parents[2] / "seeds" / "attention"


async def test_paraphrase_requires_contract_and_rechecks_sources(client, db, monkeypatch):
    owner = (await client.get("/api/learner/me")).json()["id"]
    doc = Document(title="Synthetic", source_type="manual")
    db.add(doc)
    await db.flush()
    version = DocumentVersion(document_id=doc.id, version=1, content_hash="v1")
    db.add(version)
    await db.flush()
    chunk = Chunk(id="source", document_version_id=version.id, ordinal=0, text="Use initial count.")
    db.add(chunk)
    for identifier, contract in [("eligible", "contract"), ("other-hint", "other")]:
        db.add(
            TutorAnswer(
                id=identifier,
                learner_id=owner,
                turn_id=identifier,
                surface="tutor",
                request_json={"text": "retention"},
                text="Use initial count.",
                fingerprint=identifier,
                metadata_json={
                    "skill_id": "skill",
                    "teaching_action": "explain",
                    "questioning_style": "explicit",
                    "teaching_contract_key": contract,
                    "sources": [{"chunk_id": chunk.id}],
                    "source_text_hashes": {
                        chunk.id: hashlib.sha256(chunk.text.encode()).hexdigest()
                    },
                },
            )
        )
    await db.commit()
    for identifier in ["eligible", "other-hint"]:
        await put(db, owner, identifier, identifier, "key", [1.0, 0.0])

    async def identity(*args):
        return ModelSpec(registry_id="local", provider="ollama", model="local"), "key"

    mutate = False

    async def embed(*args):
        assert not db.in_transaction()
        if mutate:
            chunk.text = "Changed source."
            await db.commit()
        return [[1.0, 0.0]]

    monkeypatch.setattr(answer_semantic, "identity", identity)
    monkeypatch.setattr(answer_semantic.OllamaProvider, "embed", embed)
    args = (
        db,
        Settings(),
        owner,
        "skill",
        "Compare group proportions",
        "explain",
        "explicit",
        "contract",
    )
    assert (
        await literal(
            db, owner, "skill", "Compare group proportions", "explain", "explicit", "contract"
        )
        == []
    )
    assert [row["answer_id"] for row in await lesson_semantic.retrieve(*args)] == ["eligible"]
    mutate = True
    assert await lesson_semantic.retrieve(*args) == []
    mutate = False
    chunk.text = "Use initial count."
    db.add(TutorAnswerFeedback(learner_id=owner, answer_id="eligible", verdict="incorrect"))
    await db.commit()
    assert await lesson_semantic.retrieve(*args) == []


async def test_semantic_failure_preserves_turn_and_schedules_index(client, db, monkeypatch):
    from app.api import answer_jobs

    await load_seed(db, SEED)
    await seed_defaults(db, installed_ollama_tags={"llama3.1:8b", "gemma3:12b"})
    session = (await client.post("/api/sessions", json={"mode": "steady", "energy": 3})).json()

    async def unavailable(*args):
        raise TimeoutError("Synthetic timeout")

    indexed = []

    async def index(*args, **kwargs):
        indexed.append(args[2])
        return {}

    monkeypatch.setattr(lesson_semantic, "retrieve", unavailable)
    monkeypatch.setattr(answer_jobs, "populate", index)
    for route in ("turn", "stream"):
        response = await client.post(
            "/api/tutor/" + route, json={"session_id": session["id"], "text": "Explain"}
        )
        assert response.status_code == 200, response.text
        if route == "turn":
            assert response.json()["answer_id"]
            assert response.json()["memory_answers"] == []
        else:
            assert "event: done" in response.text
            assert "event: error" not in response.text
    assert len(indexed) == 2


async def test_literal_history_is_rechecked_after_semantic_failure(client, db, monkeypatch):
    from app.orchestrator import tutor

    await load_seed(db, SEED)
    await seed_defaults(db, installed_ollama_tags={"llama3.1:8b", "gemma3:12b"})
    session = (await client.post("/api/sessions", json={"mode": "steady", "energy": 3})).json()
    valid = True
    calls = 0

    async def literal_result(*args):
        nonlocal calls
        calls += 1
        return [{"answer_id": "prior", "excerpt": "Historical"}] if valid else []

    async def changing(*args):
        nonlocal valid
        valid = False
        raise TimeoutError("Synthetic timeout after history changed")

    monkeypatch.setattr(tutor, "lesson_memory", literal_result)
    monkeypatch.setattr(lesson_semantic, "retrieve", changing)
    reply = await client.post(
        "/api/tutor/turn", json={"session_id": session["id"], "text": "Explain"}
    )
    assert reply.status_code == 200, reply.text
    assert calls == 2
    assert reply.json()["memory_answers"] == []
