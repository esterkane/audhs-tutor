"""Programming exercises (P8): a small catalogue of source-linked code exercises stored as
`assessment` rows (kind `code`) on their skill node. The learner's code runs **in the browser**
(Pyodide in a Web Worker: no host execution, no network after the runtime loaded, in-memory
filesystem, timeout + output cap) — the backend never executes learner or model code. The client
sends back the deterministic check results; the kernel grades them per criterion, records
`application` evidence through the ordinary grader and schedules a delayed transfer item.

Trust boundary (single-learner local app): the check results come from the learner's own browser;
they are recorded as `grader_level=deterministic` with `source=client-pyodide` in the attempt.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Assessment, AssessmentRubric, ChunkProvenance, SkillNode
from app.kernel import skill_graph
from app.schemas.grading import CriterionResult, GradeResult

KIND = "code"
MAX_ANSWER_CHARS = 20_000
MAX_HINTS = 3


@dataclass
class Check:
    name: str
    criterion: str
    code: str  # Python run after the learner's code in the same namespace; must not raise


@dataclass
class Exercise:
    exercise_id: str
    skill_slug: str
    title: str
    prompt: str
    starter_code: str
    success_criteria: list[str]
    checks: list[Check]
    hints: list[str]
    solution: str
    check_question: str
    check_rubric: list[dict[str, Any]] = field(default_factory=list)
    packages: list[str] = field(default_factory=list)
    timeout_s: int = 10
    max_output_chars: int = 20_000


CATALOGUE: dict[str, Exercise] = {
    "attn-scaled-softmax": Exercise(
        exercise_id="attn-scaled-softmax",
        skill_slug="attn-scaled",
        title="Scaled dot-product attention in numpy",
        prompt=(
            "Implement `softmax(x)` (row-wise, numerically stable) and "
            "`scaled_attention(Q, K, V)` that returns the attention output for query, key and value "
            "matrices of shape (n, d_k), (m, d_k), (m, d_v). Scores are Q·Kᵀ divided by √d_k, "
            "turned into weights with softmax over each row, then applied to V."
        ),
        starter_code=(
            "import numpy as np\n\n"
            "def softmax(x):\n"
            '    """Row-wise softmax; subtract the row max first so exp() cannot overflow."""\n'
            "    ...\n\n"
            "def scaled_attention(Q, K, V):\n"
            '    """Return softmax(Q K^T / sqrt(d_k)) V."""\n'
            "    ...\n"
        ),
        success_criteria=[
            "softmax rows sum to 1 and are stable for large inputs",
            "scores are scaled by 1/sqrt(d_k) before the softmax",
            "the output has shape (n, d_v) and matches a reference on a small example",
        ],
        checks=[
            Check(
                name="softmax_rows",
                criterion="softmax rows sum to 1 and are stable for large inputs",
                code=(
                    "import numpy as np\n"
                    "_s = softmax(np.array([[1000.0, 1000.0], [1.0, 2.0]]))\n"
                    "assert np.allclose(_s.sum(axis=1), 1.0), 'rows must sum to 1'\n"
                    "assert np.isfinite(_s).all(), 'large inputs must not overflow'\n"
                    "assert abs(_s[1, 1] - 0.7310585786) < 1e-6, 'softmax([1,2]) second entry ~0.731'\n"
                ),
            ),
            Check(
                name="scaling",
                criterion="scores are scaled by 1/sqrt(d_k) before the softmax",
                code=(
                    "import numpy as np\n"
                    "_Q = np.array([[1.0, 0.0, 0.0, 0.0]]); _K = np.array([[4.0, 0, 0, 0], [0, 4.0, 0, 0]])\n"
                    "_V = np.array([[1.0], [0.0]])\n"
                    "_out = scaled_attention(_Q, _K, _V)\n"
                    "_expected = 1.0 / (1.0 + np.exp(-2.0))  # score 4/sqrt(4)=2 vs 0 → sigmoid(2)\n"
                    "assert abs(float(_out[0, 0]) - _expected) < 1e-6, "
                    "f'expected weight on V[0] ≈ 0.881 (softmax of scaled scores [2, 0]); "
                    "got {float(_out[0, 0]):.3f}'\n"
                ),
            ),
            Check(
                name="shape_and_reference",
                criterion="the output has shape (n, d_v) and matches a reference on a small example",
                code=(
                    "import numpy as np\n"
                    "_rng = np.random.default_rng(0)\n"
                    "_Q, _K, _V = _rng.normal(size=(3, 8)), _rng.normal(size=(5, 8)), _rng.normal(size=(5, 2))\n"
                    "_out = scaled_attention(_Q, _K, _V)\n"
                    "assert _out.shape == (3, 2), f'output shape must be (n, d_v) = (3, 2); got {_out.shape}'\n"
                    "_expected = np.array([[0.892289, -0.652128], [0.622313, -0.020145], [0.736093, -0.300997]])\n"
                    "assert np.allclose(_out, _expected, atol=1e-5), "
                    "f'first row expected {_expected[0].round(3).tolist()}, "
                    "got {np.asarray(_out)[0].round(3).tolist()}'\n"
                ),
            ),
        ],
        hints=[
            "softmax works per row: which axis do max and sum reduce over, and what does keepdims=True buy you?",
            "Which dimension is d_k? Look at Q.shape. The prompt gives the scaling — does it "
            "belong before or after the softmax?",
            "The last step is a matrix product: weights of shape (n, m) times V of shape (m, d_v) gives (n, d_v).",
        ],
        solution=(
            "import numpy as np\n\n"
            "def softmax(x):\n"
            "    z = x - x.max(axis=-1, keepdims=True)\n"
            "    e = np.exp(z)\n"
            "    return e / e.sum(axis=-1, keepdims=True)\n\n"
            "def scaled_attention(Q, K, V):\n"
            "    d_k = Q.shape[-1]\n"
            "    scores = Q @ K.T / np.sqrt(d_k)\n"
            "    return softmax(scores) @ V\n"
        ),
        check_question=(
            "Check question: what happens to the softmax weights if you *forget* the 1/sqrt(d_k) "
            "factor and d_k grows to 512? One sentence."
        ),
        check_rubric=[
            {
                "criterion": "names the effect: scores grow with d_k, softmax saturates / becomes peaked",
                "keywords": ["saturat", "peak", "one-hot", "grow", "large", "sharp"],
            },
            {
                "criterion": "mentions the consequence for gradients or attention spread",
                "keywords": ["gradient", "vanish", "spread", "attend", "flat", "uniform"],
            },
        ],
        packages=["numpy"],
    ),
}


def for_slug(slug: str) -> Exercise | None:
    return next((e for e in CATALOGUE.values() if e.skill_slug == slug), None)


async def sources_for(db: AsyncSession, node: SkillNode) -> list[dict[str, str]]:
    """Citations of the node's learning object sources (source-linked exercise)."""
    lo = await skill_graph.learning_object_for(db, node.id)
    ids = [str(c) for c in (lo.sources_json if lo else []) if isinstance(c, str)][:6]
    if not ids:
        return []
    rows = (
        await db.execute(select(ChunkProvenance).where(ChunkProvenance.chunk_id.in_(ids)))
    ).scalars()
    out = []
    for prov in rows:
        parts = [p for p in (prov.course, prov.section, prov.lecture) if p]
        out.append({"chunk_id": prov.chunk_id, "citation": "[" + " › ".join(parts) + "]"})
    return out


async def ensure_check_item(db: AsyncSession, node: SkillNode, ex: Exercise) -> Assessment:
    """The check question as an ordinary explain-back item on the node (rubric-graded, one card),
    so the question is answered and recorded — not just shown."""
    rows = (
        await db.execute(
            select(Assessment).where(
                Assessment.skill_id == node.id, Assessment.kind == "explain_back"
            )
        )
    ).scalars()
    for a in rows:
        if a.item_json.get("exercise_id") == ex.exercise_id:
            return a
    rubric = AssessmentRubric(criteria_json=ex.check_rubric, version=1)
    db.add(rubric)
    await db.flush()
    a = Assessment(
        skill_id=node.id,
        kind="explain_back",
        rubric_id=rubric.id,
        item_json={"exercise_id": ex.exercise_id, "prompt": ex.check_question, "role": "check"},
    )
    db.add(a)
    await db.commit()
    return a


async def ensure_exercise(db: AsyncSession, node: SkillNode) -> Assessment | None:
    """The catalogue exercise for this node as an assessment row (created once). None when the
    catalogue has nothing for the node."""
    ex = for_slug(node.slug)
    if ex is None:
        return None
    rows = (
        await db.execute(
            select(Assessment).where(Assessment.skill_id == node.id, Assessment.kind == KIND)
        )
    ).scalars()
    for a in rows:
        if a.item_json.get("exercise_id") == ex.exercise_id:
            return a
    check = await ensure_check_item(db, node, ex)
    a = Assessment(  # a concurrent first request may race us: re-check after the commit
        skill_id=node.id,
        kind=KIND,
        rubric_id=None,
        item_json=await _item_for(db, node, ex, check.id),
    )
    db.add(a)
    await db.commit()
    rows = (
        await db.execute(
            select(Assessment)
            .where(Assessment.skill_id == node.id, Assessment.kind == KIND)
            .order_by(Assessment.id)
        )
    ).scalars()
    first = next((r for r in rows if r.item_json.get("exercise_id") == ex.exercise_id), a)
    if first.id != a.id:
        await db.delete(a)
        await db.commit()
    return first


def policy_for(ex: Exercise) -> dict[str, Any]:
    """What the sandbox enforces — worded as what is actually enforced, no more."""
    return {
        "where": "your browser, in a Web Worker (Pyodide) — never on the backend host",
        "network": (
            "best effort: fetch/XHR/WebSocket and script loading are removed from the worker after "
            "the runtime loads; the real boundary is the browser's worker sandbox — your code cannot "
            "read this Mac's files or run on the backend"
        ),
        "filesystem": "in-memory only, discarded when the worker stops; no host files",
        "runtime_download": "the pinned Pyodide release + "
        + ", ".join(ex.packages)
        + " are served by this app from its own origin (installed once by `make pyodide`); "
        "nothing is fetched from a CDN",
        "timeout_s": ex.timeout_s,
        "output_cap_chars": ex.max_output_chars,
        "run_vs_submit": "Run only executes; Submit records an assessed attempt (confidence first)",
    }


async def _item_for(
    db: AsyncSession, node: SkillNode, ex: Exercise, check_id: str
) -> dict[str, Any]:
    return {
        "exercise_id": ex.exercise_id,
        "title": ex.title,
        "prompt": ex.prompt,
        "starter_code": ex.starter_code,
        "success_criteria": ex.success_criteria,
        "checks": [{"name": c.name, "criterion": c.criterion, "code": c.code} for c in ex.checks],
        "hints": ex.hints,
        "solution": ex.solution,
        "check_question": ex.check_question,
        "check_assessment_id": check_id,
        "packages": ex.packages,
        "timeout_s": ex.timeout_s,
        "max_output_chars": ex.max_output_chars,
        "sources": await sources_for(db, node),
        "runtime": "pyodide-worker",
    }


def public_item(item: dict[str, Any]) -> dict[str, Any]:
    """Everything the client needs to run and check — never the solution or the hints."""
    return {k: v for k, v in item.items() if k not in ("solution", "hints", "check_question")}


def hint(item: dict[str, Any], level: int) -> tuple[str, int]:
    """Hint ladder: one step at a time; level clamps to the last hint."""
    hints: list[str] = list(item.get("hints") or [])
    if not hints:
        return "No hint recorded for this exercise.", 0
    lvl = max(1, min(level, len(hints)))
    return hints[lvl - 1], lvl


def grade_code(item: dict[str, Any], answer: str) -> tuple[GradeResult, bool | None]:
    """Deterministic grade from the client's check results. `answer` is JSON:
    {code, results: [{name, passed, detail}], truncated?, error?}. Missing or unknown checks count
    as failed; an error (syntax/runtime/timeout) before the checks fails every criterion, with the
    error text as the evidence."""
    try:
        payload = json.loads(answer) if answer else {}
    except json.JSONDecodeError as e:
        raise ValueError("submission must be JSON with code and check results") from e
    if not isinstance(payload, dict) or not isinstance(payload.get("code"), str):
        raise ValueError("submission must carry the code that was run")
    checks: list[dict[str, Any]] = list(item.get("checks") or [])
    error = str(payload.get("error") or "").strip()
    raw_results = payload.get("results")
    # an error before the checks means no check ran: results next to an error are ignored
    results: list[Any] = raw_results if isinstance(raw_results, list) and not error else []
    by_name = {
        str(r.get("name")): r for r in results if isinstance(r, dict) and r.get("name") is not None
    }
    crit: list[CriterionResult] = []
    for c in checks:
        r = by_name.get(str(c["name"]))
        if error and r is None:
            crit.append(
                CriterionResult(criterion=c["criterion"], passed=False, evidence=error[:300])
            )
        elif r is None:
            crit.append(
                CriterionResult(criterion=c["criterion"], passed=False, evidence="check not run")
            )
        else:
            crit.append(
                CriterionResult(
                    criterion=c["criterion"],
                    passed=bool(r.get("passed")),
                    evidence=str(r.get("detail") or ("passed" if r.get("passed") else "failed"))[
                        :300
                    ],
                )
            )
    solution_shown = bool(payload.get("solution_shown"))
    passed_n = sum(1 for c in crit if c.passed)
    total = len(crit) or 1
    correct: bool | None = True if passed_n == total else (False if passed_n == 0 else None)
    failed = [c for c in crit if not c.passed]
    if error:
        feedback = f"Your code stopped before the checks: {error[:200]}"
        next_step = "Fix the error the runtime reported, run again, then submit."
    elif not failed:
        feedback = f"All {total} checks passed."
        next_step = str(
            item.get("check_question") or "Next: explain your solution in one sentence."
        )
    else:
        feedback = f"{passed_n} of {total} checks passed. Not yet: " + "; ".join(
            f"{c.criterion} ({c.evidence})" for c in failed
        )
        next_step = (
            "Run the failing check's message against your code, change one thing, run again."
        )
    if payload.get("truncated"):
        feedback += " (Output was cut at the limit.)"
    if solution_shown:
        feedback += " Submitted after the full solution was shown: recorded at half weight."
    return (
        GradeResult(
            criterion_results=crit,
            misconception=None,
            confidence=0.5 if solution_shown else 1.0,
            feedback=feedback,
            next_step=next_step,
        ),
        correct,
    )
