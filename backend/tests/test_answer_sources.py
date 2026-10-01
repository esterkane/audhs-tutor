import hashlib

from httpx import AsyncClient
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Chunk, Document, DocumentVersion, LearningEvent, ModelCall, TutorAnswer


async def test_source_status_is_owned_bounded_and_not_correctness(
    client: AsyncClient, db: AsyncSession
) -> None:
    owner = (await client.get("/api/learner/me")).json()["id"]
    document = Document(title="Synthetic source", source_type="manual")
    db.add(document)
    await db.flush()
    old = DocumentVersion(document_id=document.id, content_hash="old", version=1)
    new = DocumentVersion(document_id=document.id, content_hash="new", version=2)
    db.add_all([old, new])
    await db.flush()
    for identifier in ("same", "changed", "unknown"):
        db.add(Chunk(id=identifier, document_version_id=old.id, ordinal=0, text="current"))
    digest = hashlib.sha256(b"current").hexdigest()
    answer = TutorAnswer(
        id="answer",
        learner_id=owner,
        turn_id="answer",
        surface="tutor",
        request_json={},
        text="Not necessarily correct",
        fingerprint="answer",
        metadata_json={
            "sources": [{"chunk_id": i} for i in ("same", "changed", "unknown", "missing")],
            "source_text_hashes": {"same": digest, "changed": "0" * 64},
        },
    )
    db.add(answer)
    await db.commit()
    response = await client.get("/api/answers/answer/source-status")
    assert response.status_code == 200, response.text
    result = response.json()
    assert result == {
        "sources": [
            {"chunk_id": "same", "status": "unchanged", "newer_version": True},
            {"chunk_id": "changed", "status": "changed", "newer_version": True},
            {"chunk_id": "unknown", "status": "unverifiable", "newer_version": True},
            {"chunk_id": "missing", "status": "missing", "newer_version": False},
        ],
        "omitted": 0,
    }
    assert (await client.get("/api/answers/absent/source-status")).status_code == 404
    import pytest

    from app.db.answer_sources import check

    with pytest.raises(KeyError):
        await check(db, "foreign", "answer")
    answer.metadata_json = {"sources": [{"chunk_id": str(i)} for i in range(103)]}
    await db.commit()
    result = (await client.get("/api/answers/answer/source-status")).json()
    assert len(result["sources"]) == 100
    assert result["omitted"] == 3
    answer.metadata_json = {}
    await db.commit()
    assert (await client.get("/api/answers/answer/source-status")).json() == {
        "sources": [],
        "omitted": 0,
    }
    for model in (LearningEvent, ModelCall):
        assert await db.scalar(select(func.count()).select_from(model)) == 0
