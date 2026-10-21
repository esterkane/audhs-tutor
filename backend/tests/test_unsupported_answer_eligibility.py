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
