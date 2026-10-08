"""One frozen read of review semantics and display; no scheduling or model work."""

import copy
import hmac
from typing import Any

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.content_versions import token
from app.core.errors import AppError
from app.db.models import (
    Assessment,
    AssessmentRubric,
    MemoryState,
    QuestionState,
    ReviewItem,
    SkillNode,
)
from app.kernel import question_state


async def snapshot(db: AsyncSession, learner_id: str, item_id: str) -> dict[str, Any]:
    reference = question_state.review_reference()
    row = (
        (
            await db.execute(
                select(
                    ReviewItem.id,
                    ReviewItem.learner_id,
                    ReviewItem.skill_id,
                    ReviewItem.object_id,
                    ReviewItem.item_type,
                    ReviewItem.prompt_json,
                    ReviewItem.active,
                    QuestionState.state.label("question_state"),
                    QuestionState.revision.label("question_revision"),
                    SkillNode.title.label("skill_title"),
                    Assessment.id.label("assessment_id"),
                    Assessment.skill_id.label("assessment_skill_id"),
                    Assessment.owner_learner_id.label("_assessment_owner"),
                    Assessment.kind,
                    Assessment.item_json,
                    Assessment.rubric_id,
                    AssessmentRubric.version,
                    AssessmentRubric.criteria_json,
                    MemoryState.due,
                    MemoryState.state,
                )
                .select_from(ReviewItem)
                .outerjoin(SkillNode, SkillNode.id == ReviewItem.skill_id)
                .outerjoin(
                    Assessment,
                    and_(
                        Assessment.id == reference,
                        func.coalesce(ReviewItem.prompt_json["type"].as_string(), "") != "vocab",
                    ),
                )
                .outerjoin(
                    QuestionState,
                    and_(
                        QuestionState.assessment_id == Assessment.id,
                        QuestionState.learner_id == learner_id,
                    ),
                )
                .outerjoin(AssessmentRubric, AssessmentRubric.id == Assessment.rubric_id)
                .outerjoin(
                    MemoryState,
                    and_(
                        MemoryState.review_item_id == ReviewItem.id,
                        MemoryState.learner_id == learner_id,
                    ),
                )
                .where(ReviewItem.id == item_id, ReviewItem.learner_id == learner_id)
            )
        )
        .mappings()
        .one_or_none()
    )
    if row is None:
        raise AppError("not_found", "Review item not found.", 404)
    result = copy.deepcopy(dict(row))
    owner = result.pop("_assessment_owner")
    if owner is not None and owner != learner_id:
        raise AppError("not_found", "Review item not found.", 404)
    result["active"] = bool(result["active"]) and result["question_state"] in (None, "active")
    result["display"] = display(result)
    return result


def display(content: dict[str, Any]) -> dict[str, Any]:
    prompt = content["prompt_json"]
    question, options, reveal = str(prompt.get("q", "")), None, ""
    if prompt.get("type") == "vocab":
        example = f" — e.g. {prompt['example']}" if prompt.get("example") else ""
        reveal = f"{prompt.get('a', '')}{example}"
    elif content["assessment_id"] is not None:
        item, kind = content["item_json"], content["kind"]
        if kind == "mcq":
            question, options = item["question"], item["options"]
            reveal = f"{options[int(item['answer'])]} — {item.get('explanation', '')}".strip(" —")
        elif kind == "cloze":
            question, reveal = item["text"], str(item["answers"][0])
        elif kind == "code":
            question = str(item.get("check_question") or item.get("prompt") or "")
            reveal = "A complete answer covers: " + "; ".join(item.get("success_criteria") or [])
        else:
            question = item["prompt"]
            reveal = "A complete answer covers: " + "; ".join(
                c["criterion"] for c in content["criteria_json"] or []
            )
    return {"question": question, "options": options, "reveal": reveal}


def content_token(content: dict[str, Any]) -> str:
    # Scheduling changes are not content changes. Skill title is displayed context.
    return token(
        {
            "domain": "review-content.v1",
            **{key: value for key, value in content.items() if key not in {"due", "state"}},
        }
    )


def validate(content: dict[str, Any], supplied: str | None, *, during_write: bool = False) -> None:
    code = "review_content_changed_during_rating" if during_write else "review_content_changed"
    if not supplied:
        raise AppError(
            "review_content_required",
            "Refresh this review item before rating. Your recall draft is retained.",
            409,
        )
    if not content["active"] or not hmac.compare_digest(
        content_token(content).encode(), supplied.encode()
    ):
        raise AppError(
            code,
            "Review content changed. No review was recorded. Refresh and review the item again."
            if not during_write
            else "Review content changed after submission. Check the saved rating before trying again.",
            409,
        )
