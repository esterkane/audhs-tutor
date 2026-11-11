"""Optional comparison cards. Preserve each independent FSRS schedule and rating history."""

from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import MemoryState, ReviewItem
from app.kernel import memory
from app.kernel.knowledge_authoring import accepted_case_comparison

KIND = "authored_case"


async def sync_pair(db: AsyncSession, learner_id: str, skill_id: str, raw: Any) -> None:
    pair = accepted_case_comparison(raw)
    active_id = pair.comparison_id if pair and pair.schedule_pair else None
    # Only this learner's explicit paired-card family is managed by the material revision.
    cards = await db.scalars(
        select(ReviewItem).where(
            ReviewItem.learner_id == learner_id,
            ReviewItem.skill_id == skill_id,
            ReviewItem.item_type == KIND,
            ReviewItem.active.is_(True),
        )
    )
    for card in cards:
        if card.prompt_json.get("pair") != active_id:
            card.active = False
    if pair is None or active_id is None:
        return
    for side, case in (("a", pair.case_a), ("b", pair.case_b)):
        fails = side == pair.failing_case
        prompt = {
            "type": KIND,
            "ref": f"authored-case:{active_id}:{side}",
            "pair": active_id,
            "side": side,
            "q": f"Case {side.upper()}: {case}\nDoes this case fail? Explain the distinction.",
            "a": f"{'This is the failing case.' if fails else 'This is the contrasting case.'} "
            f"Case {pair.failing_case.upper()} fails. {pair.rationale}",
        }
        card, _ = await memory.ensure_item(db, learner_id, skill_id, KIND, prompt, commit=False)
        card.active = True


def group_due_pairs(
    admitted: list[tuple[ReviewItem, MemoryState]],
) -> tuple[list[tuple[ReviewItem, MemoryState]], dict[str, str]]:
    """Only reorder the already eligible, scoped, capped cohort; unmarked cards keep relative order."""
    peers: dict[tuple[str, str, str], dict[str, int]] = {}
    for i, (card, _) in enumerate(admitted):
        p = card.prompt_json
        if (
            card.item_type == KIND
            and p.get("type") == KIND
            and isinstance(p.get("pair"), str)
            and p.get("side") in ("a", "b")
        ):
            peers.setdefault((card.learner_id, card.skill_id, p["pair"]), {})[p["side"]] = i
    partner = {}
    for sides in peers.values():
        if len(sides) == 2:
            first, second = sorted(sides.values())
            partner[first] = second
    emitted: set[int] = set()
    result = []
    for i, row in enumerate(admitted):
        if i not in emitted:
            result.append(row)
            if i in partner:
                second = partner[i]
                result.append(admitted[second])
                emitted.add(second)
    return result, {admitted[i][0].id: admitted[j][0].id for i, j in partner.items()}
