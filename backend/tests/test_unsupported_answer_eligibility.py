from app.db.answer_eligibility import excluded_answer_ids
from app.db.models import TutorAnswer


async def test_citation_flag_excludes_only_owned_flagged_answers_and_preserves_history(client, db):
    owner = (await client.get("/api/learner/me")).json()["id"]
    for identifier, flags in [
        ("flagged", ["unsupported_numeric_citation"]),
        ("mode-flagged", ["socratic_format_mismatch"]),
        ("clean", []),
        ("other-flag", ["untrusted"]),
        ("legacy", None),
    ]:
        db.add(
            TutorAnswer(
                id=identifier,
                learner_id=owner,
                turn_id=identifier,
                surface="tutor",
                request_json={"text": "Synthetic question"},
                text="Synthetic saved answer",
                fingerprint=identifier,
                metadata_json={} if flags is None else {"flagged": flags},
            )
        )
    await db.commit()
    assert set(await db.scalars(excluded_answer_ids(owner))) == {"flagged", "mode-flagged"}
    assert list(await db.scalars(excluded_answer_ids("another-owner"))) == []
    # Exclusion is from generated-answer reuse, never from private history.
    response = await client.get("/api/answers/flagged")
    assert response.status_code == 200
    assert response.json()["text"] == "Synthetic saved answer"
    assert response.json()["metadata"]["flagged"] == ["unsupported_numeric_citation"]


async def test_legacy_socratic_explanations_need_validation_before_reuse(client, db):
    owner = (await client.get("/api/learner/me")).json()["id"]
    for identifier, checked in [("unchecked", None), ("checked", True)]:
        metadata = {"questioning_style": "socratic", "teaching_action": "explain"}
        if checked is not None:
            metadata["socratic_format_checked"] = checked
        db.add(
            TutorAnswer(
                id=identifier,
                learner_id=owner,
                turn_id=identifier,
                surface="tutor",
                request_json={},
                text="What comes next?",
                fingerprint=identifier,
                metadata_json=metadata,
            )
        )
    await db.commit()
    assert set(await db.scalars(excluded_answer_ids(owner))) == {"unchecked"}
    assert (await client.get("/api/answers/unchecked")).status_code == 200


async def test_truncated_request_excludes_reuse_without_deleting_history_or_cached_vectors(
    client, db
):
    from app.db.answer_vectors import load, put

    owner = (await client.get("/api/learner/me")).json()["id"]
    for identifier, dropped in [
        ("lost-question", ["request:truncated"]),
        ("other-drop", ["retrieved:unused"]),
        ("empty-drop", []),
        ("no-drop-field", None),
    ]:
        db.add(
            TutorAnswer(
                id=identifier,
                learner_id=owner,
                turn_id=identifier,
                surface="tutor",
                request_json={"text": "Original complete question"},
                text="Original saved reply",
                fingerprint=identifier,
                metadata_json={} if dropped is None else {"dropped": dropped},
            )
        )
    await db.commit()
    assert await put(db, owner, "lost-question", "lost-question", "test-model", [1.0, 0.0])
    assert set(await db.scalars(excluded_answer_ids(owner))) == {"lost-question"}
    assert list(await db.scalars(excluded_answer_ids("another-owner"))) == []
    assert await load(db, owner, ["lost-question"], "test-model", 2) == {}
    response = await client.get("/api/answers/lost-question")
    assert response.status_code == 200
    assert response.json()["text"] == "Original saved reply"
    assert response.json()["metadata"]["dropped"] == ["request:truncated"]
