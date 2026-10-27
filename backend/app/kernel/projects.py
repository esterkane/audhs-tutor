"""Focused application briefs. No SQL/model execution and no mastery writes."""

from typing import Any

from sqlalchemy import select
from sqlalchemy.dialects.sqlite import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import LearningProject

BRIEFS: list[dict[str, Any]] = [
    {
        "slug": "supabase-postgres-support",
        "workspace": "/projects/supabase",
        "title": "Supabase request and access-control lab",
        "topic": "Supabase",
        "objective": (
            "Trace a request from JWT identity through grants and row-level security; diagnose "
            "the smallest failing boundary."
        ),
        "build": [
            "Use the linked Supabase/PostgreSQL project in a disposable local environment.",
            "Install lab 01 in the disposable lab database.",
            (
                "Record the current database role, JWT subject, schema/table privileges and RLS "
                "policies before changing anything."
            ),
        ],
        "test": [
            "Show the original failing query and exact error.",
            "Demonstrate the minimal fix with the authenticated role, not the administrator.",
            "Show both an allowed own-row read and a denied cross-user read.",
        ],
        "reflect": (
            "Explain why table privileges and row visibility are separate checks. State what your"
            " test does not prove."
        ),
        "source": "https://github.com/esterkane/kanguroo-supabase-tutor",
    },
    {
        "slug": "postgresql-query-plan",
        "title": "PostgreSQL query-plan investigation",
        "topic": "PostgreSQL",
        "objective": "Use real query plans to explain a performance change without inventing a cause.",
        "build": [
            "Create a disposable table and a reproducible data generator.",
            "Write a selective query and record EXPLAIN (ANALYZE, BUFFERS).",
            "Add an index and repeat the identical query.",
        ],
        "test": [
            "Compare returned rows before and after the index.",
            "Record actual versus estimated rows and buffer access.",
            "Repeat measurements and report variation instead of one timing as proof.",
        ],
        "reflect": "Distinguish an observed plan change, a plausible cause and a demonstrated performance benefit.",
        "source": "https://www.postgresql.org/docs/current/using-explain.html",
    },
    {
        "slug": "elasticsearch-relevance",
        "title": "Elasticsearch lexical and hybrid relevance",
        "topic": "Elasticsearch",
        "objective": "Build a small reproducible search evaluation with explicit relevance judgments.",
        "build": [
            "Author a synthetic document set, query set and relevance labels.",
            "Create explicit mappings and index the documents.",
            "Compare BM25 with a separately configured hybrid retrieval run.",
        ],
        "test": [
            "Verify filters and exclusions with known expected document IDs.",
            "Measure precision/recall or ranking metrics on held-out queries.",
            "Keep failed examples and configuration versions.",
        ],
        "reflect": (
            "Explain where hybrid retrieval helped or harmed your measured queries; do not claim "
            "universal superiority."
        ),
        "source": "https://www.elastic.co/docs/solutions/search",
    },
    {
        "slug": "vector-search-evaluation",
        "title": "Vector-search evaluation and isolation",
        "topic": "Vector search",
        "objective": "Separate embedding quality, nearest-neighbor approximation and metadata filtering.",
        "build": [
            "Write synthetic text pairs with relevant and confusing examples.",
            "Record the embedding model, vector dimension and distance metric.",
            "Keep indexing and query preprocessing consistent.",
        ],
        "test": [
            "Compare approximate neighbors against a small exact-search baseline.",
            "Assert filtered document IDs, including empty matches.",
            "Report quality and latency separately with repeated runs.",
        ],
        "reflect": "Identify which results are semantic judgments and which are deterministic filter checks.",
        "source": "https://github.com/pgvector/pgvector",
    },
    {
        "slug": "qdrant-filtered-search",
        "title": "Qdrant filtered retrieval and rebuild",
        "topic": "Qdrant",
        "objective": "Prove filtering and index rebuild behavior on synthetic vectors.",
        "build": [
            "Create a separate disposable collection with explicit vector settings.",
            "Insert labelled synthetic points with tenant and topic payloads.",
            "Create the payload indexes needed for your chosen filters.",
        ],
        "test": [
            "Assert no cross-tenant result is returned.",
            "Check zero-match and deleted-point cases.",
            "Rebuild from a saved source fixture and compare expected IDs.",
        ],
        "reflect": "Explain why a filter is not a substitute for application authorization.",
        "source": "https://qdrant.tech/documentation/",
    },
    {
        "slug": "kubernetes-recovery",
        "title": "Kubernetes deployment and failure recovery",
        "topic": "Kubernetes",
        "objective": "Diagnose a local deployment using evidence from health checks, events and logs.",
        "build": [
            "Use a disposable local cluster and namespace.",
            "Deploy a small service with readiness and liveness probes.",
            "Declare resource requests/limits and a reversible rollout.",
        ],
        "test": [
            "Observe traffic behavior when readiness fails.",
            "Reproduce a configuration failure and diagnose its events.",
            "Roll back and verify the expected version and service response.",
        ],
        "reflect": "Separate what the probes demonstrate from claims about production resilience.",
        "source": "https://kubernetes.io/docs/tutorials/",
    },
]


async def ensure_projects(db: AsyncSession, learner_id: str) -> list[LearningProject]:
    for brief in BRIEFS:
        await db.execute(
            insert(LearningProject)
            .values(
                learner_id=learner_id,
                slug=brief["slug"],
                title=brief["title"],
                topic=brief["topic"],
                objective=brief["objective"],
                brief_json={
                    k: v
                    for k, v in brief.items()
                    if k not in {"slug", "title", "topic", "objective"}
                },
            )
            .on_conflict_do_nothing(index_elements=["learner_id", "slug"])
        )
    await db.commit()
    order = {brief["slug"]: i for i, brief in enumerate(BRIEFS)}
    rows = list(
        await db.scalars(select(LearningProject).where(LearningProject.learner_id == learner_id))
    )
    return sorted(rows, key=lambda row: order.get(row.slug, 99))
