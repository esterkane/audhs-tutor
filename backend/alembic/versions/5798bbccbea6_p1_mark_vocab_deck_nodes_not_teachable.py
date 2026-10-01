"""p1 mark vocab deck nodes not teachable

Vocabulary deck nodes (`kernel/practice.vocab_deck`, slug `lang-<code>`, domain language) are
reviewed on FSRS inside the language block and never taught. `skill_graph.next_skill` now skips
nodes whose `assessment_requirements_json.teachable` is false; this data step marks the decks that
existed before P1. No schema change.

Revision ID: 5798bbccbea6
Revises: 5e3a8f8d231b
Create Date: 2026-09-20 13:02:43.998458

"""

import json
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "5798bbccbea6"
down_revision: str | Sequence[str] | None = "5e3a8f8d231b"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Data step: flag existing vocabulary deck nodes as not teachable."""
    conn = op.get_bind()
    rows = conn.execute(
        sa.text(
            "SELECT id, assessment_requirements_json FROM skill_node "
            "WHERE domain = 'language' AND slug LIKE 'lang-%'"
        )
    ).all()
    for node_id, reqs in rows:
        current = json.loads(reqs) if isinstance(reqs, str) and reqs else (reqs or {})
        if not isinstance(current, dict):
            current = {}
        current.update({"teachable": False, "kind": "vocab_deck"})
        conn.execute(
            sa.text("UPDATE skill_node SET assessment_requirements_json = :r WHERE id = :id"),
            {"r": json.dumps(current), "id": node_id},
        )


def downgrade() -> None:
    """Remove the marker again (the nodes stay)."""
    conn = op.get_bind()
    rows = conn.execute(
        sa.text(
            "SELECT id, assessment_requirements_json FROM skill_node "
            "WHERE domain = 'language' AND slug LIKE 'lang-%'"
        )
    ).all()
    for node_id, reqs in rows:
        current = json.loads(reqs) if isinstance(reqs, str) and reqs else (reqs or {})
        if isinstance(current, dict):
            current.pop("teachable", None)
            current.pop("kind", None)
        conn.execute(
            sa.text("UPDATE skill_node SET assessment_requirements_json = :r WHERE id = :id"),
            {"r": json.dumps(current), "id": node_id},
        )
