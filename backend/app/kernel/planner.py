"""Rule-based block planner v1 (ADR-0006, pedagogy session template).

Template: 0 movement primer · 1 retrieval warm-up · 2 new material (worked → faded) · 3 challenge ·
4 interleaved review · 5 domain switch · 6 confidence-rated recap. Minimum-viable session = 1 + 6.
Low-capacity = 1 + (2 or 4, short) + 6. Domain switches only at block boundaries; movement before
new material or immediately after, never during. Deterministic: same inputs → same plan.
"""

from typing import Any, Literal

from pydantic import BaseModel, Field

BlockType = Literal[
    "movement_primer",
    "retrieval",
    "new_material",
    "challenge",
    "interleaved_review",
    "domain_switch",
    "recap",
]
GRASP_CHECK_BLOCKS = {"new_material"}


class Block(BaseModel):
    type: BlockType
    planned_min: int
    node_ids: list[str] = Field(default_factory=list)
    optional: bool = False
    reason: str = ""
    grasp_check_required: bool = False
    domain: str | None = None  # language | guitar | movement for whole-domain blocks (ADR-0006)
    base_min: int | None = (
        None  # energy-3 minutes; re-planning re-scales from here, never from a guess
    )


class PlanInput(BaseModel):
    mode: str  # novelty | steady | low_capacity
    energy: int = Field(ge=1, le=5)
    due_reviews: int = 0
    next_skill_id: str | None = None
    next_skill_mastery: float = 0.0
    review_node_ids: list[str] = Field(default_factory=list)
    other_domains_available: bool = False  # language / guitar blocks exist (Stage 4)
    language_due: int = 0  # due vocabulary cards → the domain block is a language block
    guitar: bool = False  # guitar practice enabled (planner.guitar)
    preferences: dict[str, Any] = Field(default_factory=dict)


class Plan(BaseModel):
    mode: str
    energy: int
    blocks: list[Block]
    minimum_viable: list[str]
    total_min: int
    policy_version: str = "planner.v1"

    def types(self) -> list[str]:
        return [b.type for b in self.blocks]


def _scale(minutes: int, energy: int) -> int:
    """Energy 1 → 60 %, 3 → 100 %, 5 → 120 % of the planned length, never below 3 minutes."""
    factor = {1: 0.6, 2: 0.8, 3: 1.0, 4: 1.1, 5: 1.2}[energy]
    return max(3, round(minutes * factor))


def plan_session(inp: PlanInput) -> Plan:
    prefs = inp.preferences
    new_min = int(prefs.get("planner.new_material_min", 20))
    review_min = int(prefs.get("planner.review_min", 10))
    movement = str(prefs.get("planner.movement", "before"))
    want_challenge = bool(prefs.get("planner.challenge", True))
    e = inp.energy
    skill = [inp.next_skill_id] if inp.next_skill_id else []
    blocks: list[Block] = []

    retrieval = Block(
        type="retrieval",
        planned_min=_scale(7, e),
        base_min=7,
        node_ids=inp.review_node_ids[:5],
        reason=f"{inp.due_reviews} items due"
        if inp.due_reviews
        else "warm-up on the current skill",
    )
    recap = Block(
        type="recap", planned_min=5, base_min=5, reason="confidence-rated recap; always last"
    )

    if inp.mode == "low_capacity" or e <= 1:
        # 1 + (2 or 4, short) + 6 — the shortest useful path
        middle = (
            Block(
                type="interleaved_review",
                planned_min=_scale(6, max(e, 2)),
                node_ids=inp.review_node_ids[:3],
                reason="short review; energy is low",
            )
            if inp.due_reviews >= 3 or not skill
            else Block(
                type="new_material",
                planned_min=_scale(8, max(e, 2)),
                node_ids=skill,
                reason="one short idea",
                grasp_check_required=True,
            )
        )
        blocks = [retrieval, middle, recap]
        return _finish(inp, blocks)

    if movement == "before":
        blocks.append(
            Block(
                type="movement_primer",
                domain="movement",
                planned_min=5 if e >= 3 else 3,
                optional=True,
                reason="movement before new material (ADR-0006)",
            )
        )
    blocks.append(retrieval)
    if skill:
        scaffold = (
            "problem-first allowed" if inp.next_skill_mastery >= 0.6 else "worked example first"
        )
        blocks.append(
            Block(
                type="new_material",
                planned_min=_scale(new_min if inp.mode != "novelty" else new_min + 5, e),
                base_min=new_min if inp.mode != "novelty" else new_min + 5,
                node_ids=skill,
                reason=scaffold,
                grasp_check_required=True,
            )
        )
        if movement == "after":
            blocks.append(
                Block(
                    type="movement_primer",
                    domain="movement",
                    planned_min=5,
                    base_min=5,
                    optional=True,
                    reason="movement right after new material (ADR-0006)",
                )
            )
    if (
        want_challenge
        and e >= 3
        and skill
        and (inp.mode == "novelty" or inp.next_skill_mastery >= 0.3)
    ):
        blocks.append(
            Block(
                type="challenge",
                planned_min=_scale(10, e),
                base_min=10,
                node_ids=skill,
                optional=True,
                reason="critical-thinking challenge on the current skill",
            )
        )
    if inp.due_reviews or inp.review_node_ids:
        blocks.append(
            Block(
                type="interleaved_review",
                planned_min=_scale(review_min, e),
                base_min=review_min,
                node_ids=inp.review_node_ids[:8],
                reason="interleave confusable AI/ML concepts (ADR-0006)",
            )
        )
    if (inp.other_domains_available or inp.language_due or inp.guitar) and e >= 3:
        domain = "language" if inp.language_due else ("guitar" if inp.guitar else None)
        if domain is not None:
            blocks.append(
                Block(
                    type="domain_switch",
                    planned_min=_scale(10 if domain == "language" else 15, e),
                    base_min=10 if domain == "language" else 15,
                    optional=True,
                    domain=domain,
                    reason=(
                        f"{inp.language_due} vocabulary cards due (spaced, whole block, ADR-0006)"
                        if domain == "language"
                        else "guitar practice at a boundary (ADR-0006)"
                    ),
                )
            )
    blocks.append(recap)
    return _finish(inp, blocks)


def _finish(inp: PlanInput, blocks: list[Block]) -> Plan:
    plan = Plan(
        mode=inp.mode,
        energy=inp.energy,
        blocks=blocks,
        minimum_viable=["retrieval", "recap"],
        total_min=sum(b.planned_min for b in blocks),
    )
    validate_plan(plan)
    return plan


def validate_plan(plan: Plan) -> None:
    """Invariants every plan must satisfy; raises ValueError otherwise."""
    types = plan.types()
    if not types or types[-1] != "recap":
        raise ValueError("recap must be the last block")
    if "retrieval" not in types:
        raise ValueError("retrieval warm-up is mandatory (minimum-viable session)")
    first_non_movement = next(t for t in types if t != "movement_primer")
    if first_non_movement != "retrieval":
        raise ValueError("retrieval must come first (after an optional movement primer)")
    for i, t in enumerate(types):
        if t == "movement_primer":
            neighbours = {types[i - 1] if i else None, types[i + 1] if i + 1 < len(types) else None}
            if "new_material" not in neighbours and i != 0:
                raise ValueError("movement must precede or immediately follow new material")
    if types.count("new_material") > 1 or types.count("recap") > 1:
        raise ValueError("at most one new-material and one recap block")
    if plan.total_min > 90:
        raise ValueError("plan longer than 90 minutes")
    if any(b.planned_min < 3 for b in plan.blocks):
        raise ValueError("blocks shorter than 3 minutes")


def can_switch_early(block: Block, *, grasp_passed: bool | None, reason: str) -> tuple[bool, str]:
    """Early switch out of a block: new material needs a minimal grasp check unless the learner is
    saving and stopping (learner control beats completeness)."""
    if reason in ("save_and_stop", "session_end"):
        return True, "saved and stopped; nothing lost"
    if block.grasp_check_required and not grasp_passed:
        return False, "answer one recall item on this skill before switching (grasp check)"
    return True, "ok"


def replan(plan: Plan, *, from_index: int, energy: int) -> Plan:
    """Mid-session energy check-in (ADR-0006 boundaries): blocks before `from_index` are kept as
    they were; the rest are re-scaled to the new energy. At energy 1 optional blocks and the
    challenge are dropped so the minimum-viable path remains. Never applied silently — the
    caller raises an adaptation card."""
    if not 1 <= energy <= 5:
        raise ValueError("energy must be 1-5")
    old_factor = {1: 0.6, 2: 0.8, 3: 1.0, 4: 1.1, 5: 1.2}[plan.energy]
    from_index = max(0, min(from_index, len(plan.blocks)))
    kept = [b.model_copy() for b in plan.blocks[:from_index]]
    rest: list[Block] = []
    for i, b in enumerate(plan.blocks[from_index:]):
        # the first block of the tail is the one in progress: it is re-scaled, never removed
        if i > 0 and energy <= 1 and (b.optional or b.type == "challenge"):
            continue
        # base_min is the energy-3 length recorded at planning time; older plans fall back to
        # un-scaling by the plan's own energy
        base = b.base_min if b.base_min is not None else max(3, round(b.planned_min / old_factor))
        rest.append(b.model_copy(update={"planned_min": _scale(base, energy), "base_min": base}))
    blocks = kept + rest
    if not any(b.type == "recap" for b in blocks):
        blocks.append(
            Block(type="recap", planned_min=3, base_min=3, reason="always end with a recap")
        )
    out = Plan(
        mode=plan.mode,
        energy=energy,
        blocks=blocks,
        minimum_viable=plan.minimum_viable,
        total_min=sum(b.planned_min for b in blocks),
        policy_version=plan.policy_version,
    )
    validate_plan(out)
    return out
