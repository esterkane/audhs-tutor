"""An author-controlled pair is practice material, independent of generated challenges."""

from uuid import uuid4

import pytest
from sqlalchemy import func, select

from app.db.models import AssessmentAttempt, CompetencyEvidence, ModelCall, SkillNode
from app.kernel.knowledge_authoring import accepted_case_comparison
from tests.test_knowledge_authoring import complete

PAIR = {
    "case_a": "SELECT 'abc';",
    "case_b": "SELECT 'abc'::integer;",
    "failing_case": "b",
    "rationale": "Das Wort abc ist keine ganze Zahl.",
}


@pytest.mark.parametrize(
    "change",
    [
        {"case_a": "  "},
        {"case_b": PAIR["case_a"]},
        {"rationale": " "},
        {"failing_case": None},
        {"failing_case": "c"},
        {"unexpected": True},
    ],
)
def test_only_complete_distinct_authored_comparisons_are_readable(change):
    assert accepted_case_comparison(PAIR | change) is None


async def test_partial_draft_save_accept_revision_binding_and_disable(client, db):
    key = str(uuid4())
    form = complete()
    partial = {"case_a": PAIR["case_a"]}
    response = await client.post(
        "/api/knowledge-material/drafts",
        json=form | {"case_comparison": partial},
        headers={"Idempotency-Key": key},
    )
    assert response.status_code == 200, response.text
    created = response.json()
    assert created["payload"]["authoring"]["case_comparison"]["case_a"] == partial["case_a"]
    assert any(
        p["where"] == "case_comparison" and p["level"] == "error" for p in created["problems"]
    )

    async def activate(draft):
        return await client.post(
            f"/api/curriculum/drafts/{draft['id']}/publish",
            json={"expected_version": draft["version"]},
        )

    async def save(draft, extra):
        result = await client.put(
            "/api/knowledge-material/drafts/" + draft["id"],
            json=form | {"expected_version": draft["version"]} | extra,
        )
        assert result.status_code == 200, result.text
        return result.json()

    async def revise(draft):
        result = await client.post(
            f"/api/knowledge-material/drafts/{draft['id']}/revise",
            json={"expected_version": draft["version"]},
            headers={"Idempotency-Key": str(uuid4())},
        )
        assert result.status_code == 200, result.text
        return result.json()

    assert (await activate(created)).status_code == 400
    assert (
        await client.post(
            "/api/knowledge-material/drafts",
            json=form | {"case_comparison": PAIR},
            headers={"Idempotency-Key": key},
        )
    ).status_code == 409
    prepared = await save(created, {"case_comparison": PAIR})
    cue = "Look at the conversion in each expression."
    prepared = await save(prepared, {"case_comparison": PAIR | {"comparison_focus": cue}})
    prepared = await save(prepared, {"case_comparison": PAIR})
    assert prepared["payload"]["authoring"]["case_comparison"]["comparison_focus"] == cue
    prepared = await save(prepared, {"case_comparison": PAIR | {"comparison_focus": ""}})
    assert "comparison_focus" not in prepared["payload"]["authoring"]["case_comparison"]
    prepared = await save(prepared, {})
    published = (await activate(prepared)).json()["draft"]
    node = await db.scalar(
        select(SkillNode).where(SkillNode.slug == published["payload"]["skills"][0]["slug"])
    )
    uri = f"/api/knowledge-material/skills/{node.id}/reading"
    original = (await client.get(uri)).json()
    accepted = original["case_comparison"]
    assert {k: accepted[k] for k in PAIR} == PAIR and len(accepted["comparison_id"]) == 64
    revision = await revise(published)
    updated = await save(revision, {"case_comparison": PAIR | {"rationale": "Neue Begründung."}})
    assert (await client.get(uri)).json() == original
    replacement = (await activate(updated)).json()["draft"]
    revised = (await client.get(uri)).json()
    assert revised["case_comparison"]["rationale"] == "Neue Begründung."
    assert revised["case_comparison"]["comparison_id"] != accepted["comparison_id"]
    assert revised["draft_id"] != original["draft_id"]
    disabled = await save(await revise(replacement), {"case_comparison": None})
    assert (await activate(disabled)).status_code == 200
    assert (await client.get(uri)).json()["case_comparison"] is None
    for model in (AssessmentAttempt, CompetencyEvidence, ModelCall):
        assert await db.scalar(select(func.count()).select_from(model)) == 0


def test_optional_cue_preserves_legacy_fingerprints_and_binds_a_changed_cue():
    import hashlib
    import json

    from app.schemas.knowledge_authoring import CaseComparison

    old_id = hashlib.sha256(
        json.dumps(list(PAIR.values()), ensure_ascii=False, separators=(",", ":")).encode()
    ).hexdigest()
    assert CaseComparison.model_validate(PAIR).model_dump() == PAIR
    assert accepted_case_comparison(PAIR).comparison_id == old_id
    cue = "Look at the type conversion in each expression."
    accepted = accepted_case_comparison(PAIR | {"comparison_focus": cue})
    assert accepted.comparison_focus == cue and accepted.comparison_id != old_id
