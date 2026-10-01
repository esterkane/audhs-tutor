from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.db.answer_vectors import put
from app.db.models import TutorAnswer, TutorAnswerFeedback
from app.models_ai.provider import ModelSpec
from app.orchestrator import answer_semantic
from app.schemas.playground import PlaygroundContext, PlaygroundRequest


async def test_semantic_candidates_keep_scope_and_recheck_feedback(
    client: AsyncClient, db: AsyncSession, monkeypatch
) -> None:  # type: ignore[no-untyped-def]
    owner = (await client.get("/api/learner/me")).json()["id"]
    body = PlaygroundRequest(
        session_id="s",
        question="Explain proportions",
        exercise="Task",
        code="",
        learning_context=PlaygroundContext(target_id="step"),
    )
    for identifier, target in [("related", "step"), ("other-task", "other")]:
        db.add(
            TutorAnswer(
                id=identifier,
                learner_id=owner,
                turn_id=identifier,
                surface="playground",
                text="Use the initial count as denominator",
                request_json=body.model_dump(exclude={"session_id"}),
                metadata_json={"learning_context": {"target_id": target}},
                fingerprint=identifier,
            )
        )
    for i in range(260):
        db.add(
            TutorAnswer(
                id=f"z-memory-{i}",
                learner_id=owner,
                turn_id=f"z-memory-{i}",
                surface="playground",
                text="Derived response",
                fingerprint=f"z-{i}",
                request_json=body.model_dump(exclude={"session_id"}),
                metadata_json={
                    "learning_context": {"target_id": "step"},
                    "answer_memory": [{"answer_id": "related"}],
                },
            )
        )
    await db.commit()
    for identifier in ("related", "other-task"):
        await put(db, owner, identifier, identifier, "key", [1.0, 0.0])

    async def identity(*args):  # type: ignore[no-untyped-def]
        return ModelSpec(registry_id="local", provider="ollama", model="local"), "key"

    hide = False

    async def embed(*args):  # type: ignore[no-untyped-def]
        assert not db.in_transaction()
        if hide:
            db.add(TutorAnswerFeedback(learner_id=owner, answer_id="related", hidden=True))
            await db.commit()
        return [[1.0, 0.0]]

    monkeypatch.setattr(answer_semantic, "identity", identity)
    monkeypatch.setattr(answer_semantic.OllamaProvider, "embed", embed)
    found = await answer_semantic.retrieve(db, Settings(), owner, body)
    assert [row["answer_id"] for row in found] == ["related"]
    hide = True
    assert await answer_semantic.retrieve(db, Settings(), owner, body) == []
    assert await answer_semantic.retrieve(db, Settings(), "foreign", body) == []


async def test_tiny_cached_vector_does_not_break_tutor_generation(
    client, db, fake_local, monkeypatch
):  # type: ignore[no-untyped-def]
    from app.models_ai.registry import seed_defaults

    await seed_defaults(db, installed_ollama_tags={"llama3.1:8b", "gemma3:12b"})
    owner = (await client.get("/api/learner/me")).json()["id"]
    session = (await client.post("/api/sessions", json={"mode": "steady", "energy": 3})).json()
    body = PlaygroundRequest(
        session_id=session["id"],
        question="Paraphrase",
        exercise="Task",
        code="",
        learning_context=PlaygroundContext(target_id="step"),
    )
    db.add(
        TutorAnswer(
            id="tiny",
            learner_id=owner,
            turn_id="tiny",
            surface="playground",
            text="Prior reasoning",
            request_json=body.model_copy(update={"question": "Original"}).model_dump(
                exclude={"session_id"}
            ),
            metadata_json={"learning_context": {"target_id": "step"}},
            fingerprint="tiny",
        )
    )
    await db.commit()
    await put(db, owner, "tiny", "tiny", "key", [1e-300, 0.0])

    async def identity(*args):  # type: ignore[no-untyped-def]
        return ModelSpec(registry_id="local", provider="ollama", model="local"), "key"

    async def embed(*args):  # type: ignore[no-untyped-def]
        return [[1e-300, 0.0]]

    monkeypatch.setattr(answer_semantic, "identity", identity)
    monkeypatch.setattr(answer_semantic.OllamaProvider, "embed", embed)
    result = await client.post("/api/playground/tutor", json=body.model_dump())
    assert result.status_code == 200, result.text
    assert result.json()["text"] == fake_local.text
    assert result.json()["memory_answers"] == ["tiny"]


async def test_literal_answer_reported_during_semantic_lookup_is_excluded(client, db, monkeypatch):  # type: ignore[no-untyped-def]
    from app.models_ai.registry import seed_defaults

    await seed_defaults(db, installed_ollama_tags={"llama3.1:8b", "gemma3:12b"})
    owner = (await client.get("/api/learner/me")).json()["id"]
    session = (await client.post("/api/sessions", json={"mode": "steady", "energy": 3})).json()
    body = {
        "session_id": session["id"],
        "question": "group",
        "exercise": "Groups",
        "code": "",
        "learning_context": {"target_id": "step"},
    }
    original = (await client.post("/api/playground/tutor", json=body)).json()

    async def changing(*args):
        db.add(TutorAnswerFeedback(learner_id=owner, answer_id=original["answer_id"], hidden=True))
        await db.commit()
        return []

    monkeypatch.setattr(answer_semantic, "retrieve", changing)
    response = await client.post("/api/playground/tutor", json=body)
    assert response.status_code == 200, response.text
    assert response.json()["memory_answers"] == []
