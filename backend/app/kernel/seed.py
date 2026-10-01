"""Load a curriculum seed (seeds/<name>/skills.yaml + sources/*.md) idempotently."""

import hashlib
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Assessment, AssessmentRubric, LearningObject, SkillEdge, SkillNode
from app.knowledge.ingest.service import ingest_markdown


@dataclass
class SeedReport:
    skills: int = 0
    edges: int = 0
    learning_objects: int = 0
    assessments: int = 0
    documents: list[dict[str, Any]] = field(default_factory=list)


def _check_acyclic(skills: list[dict[str, Any]]) -> None:
    """Kahn over the YAML before anything is written; a cyclic seed would break every read path."""
    indeg = {s["slug"]: 0 for s in skills}
    out: dict[str, list[str]] = {s["slug"]: [] for s in skills}
    for s in skills:
        for pre in s.get("prerequisites", []):
            if pre not in indeg:
                raise ValueError(f"seed: unknown prerequisite {pre!r} for {s['slug']!r}")
            indeg[s["slug"]] += 1
            out[pre].append(s["slug"])
    queue = [k for k, v in indeg.items() if v == 0]
    seen = 0
    while queue:
        cur = queue.pop()
        seen += 1
        for nxt in out[cur]:
            indeg[nxt] -= 1
            if indeg[nxt] == 0:
                queue.append(nxt)
    if seen != len(skills):
        raise ValueError("seed: prerequisite graph has a cycle")


def _seed_key(skill: str, kind: str, item: dict[str, Any]) -> str:
    return hashlib.sha1(f"{skill}|{kind}|{json.dumps(item, sort_keys=True)}".encode()).hexdigest()[
        :16
    ]


async def load_seed(db: AsyncSession, seed_dir: Path) -> SeedReport:
    data = yaml.safe_load((seed_dir / "skills.yaml").read_text())
    domain = data.get("domain", "ai_ml")
    report = SeedReport()

    _check_acyclic(data["skills"])
    ids: dict[str, str] = {}
    for s in data["skills"]:
        node = (
            await db.execute(select(SkillNode).where(SkillNode.slug == s["slug"]))
        ).scalar_one_or_none()
        fields = dict(
            domain=domain,
            course=data.get("course"),
            title=s["title"],
            description=s.get("description", ""),
            success_criteria_json=s.get("success_criteria", []),
            assessment_requirements_json=s.get("assessment_requirements", {}),
            example_applications_json=s.get("example_applications", []),
        )
        if node is None:
            node = SkillNode(slug=s["slug"], **fields)
            db.add(node)
            await db.flush()
        else:
            for k, v in fields.items():
                setattr(node, k, v)
        ids[s["slug"]] = node.id
        report.skills += 1

    for s in data["skills"]:
        for pre in s.get("prerequisites", []):
            stmt = select(SkillEdge).where(
                SkillEdge.from_skill_id == ids[pre],
                SkillEdge.to_skill_id == ids[s["slug"]],
                SkillEdge.kind == "prerequisite",
            )
            if (await db.execute(stmt)).scalar_one_or_none() is None:
                db.add(
                    SkillEdge(
                        from_skill_id=ids[pre], to_skill_id=ids[s["slug"]], kind="prerequisite"
                    )
                )
            report.edges += 1

    for lo in data.get("learning_objects", []):
        skill_id = ids[lo["skill"]]
        obj = (
            await db.execute(select(LearningObject).where(LearningObject.skill_id == skill_id))
        ).scalar_one_or_none()
        fields = dict(
            concept=lo["concept"],
            goal=lo["goal"],
            examples_json=lo.get("examples", []),
            exercises_json=lo.get("exercises", []),
            sources_json=lo.get("sources", []),
            success_criteria_json=lo.get("success_criteria", []),
        )
        if obj is None:
            db.add(LearningObject(skill_id=skill_id, **fields))
        else:
            for k, v in fields.items():
                setattr(obj, k, v)
        report.learning_objects += 1

    for a in data.get("assessments", []):
        skill_id = ids[a["skill"]]
        item = dict(a["item"])
        key = _seed_key(a["skill"], a["kind"], item)
        item["seed_key"] = key
        existing = None
        for row in (
            await db.execute(select(Assessment).where(Assessment.skill_id == skill_id))
        ).scalars():
            if row.item_json.get("seed_key") == key:
                existing = row
                break
        if existing is None:
            rubric_id = None
            if a.get("rubric"):
                rubric = AssessmentRubric(criteria_json=a["rubric"], version=1)
                db.add(rubric)
                await db.flush()
                rubric_id = rubric.id
            db.add(
                Assessment(skill_id=skill_id, kind=a["kind"], item_json=item, rubric_id=rubric_id)
            )
        report.assessments += 1
    # retire seed assessments whose item changed (new seed_key) and that were never attempted
    from app.db.models import AssessmentAttempt

    current_keys = {
        _seed_key(a["skill"], a["kind"], dict(a["item"])) for a in data.get("assessments", [])
    }
    for row in (
        (await db.execute(select(Assessment).where(Assessment.skill_id.in_(list(ids.values())))))
        .scalars()
        .all()
    ):
        existing_key = row.item_json.get("seed_key")
        if existing_key and existing_key not in current_keys:
            attempted = (
                await db.execute(
                    select(AssessmentAttempt.id)
                    .where(AssessmentAttempt.assessment_id == row.id)
                    .limit(1)
                )
            ).first()
            if not attempted:
                await db.delete(row)
    await db.commit()

    for md in sorted((seed_dir / "sources").glob("*.md")):
        res = await ingest_markdown(
            db,
            md,
            skill_ids_by_slug=ids,
            course=data.get("course"),
            trust_tier=int(data.get("trust_tier", 2)),
        )
        report.documents.append(
            {"file": md.name, "version": res.version, "chunks": res.chunks, "changed": res.changed}
        )
    return report
