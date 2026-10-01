"""local saved answer search

Revision ID: 58e8952b930d
Revises: 1c27f2b8243b
Create Date: 2026-10-01 18:44:08.150973

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "58e8952b930d"
down_revision: str | Sequence[str] | None = "1c27f2b8243b"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    from app.db.answer_search import ANSWER_SEARCH_BACKFILL, ANSWER_SEARCH_DDL

    for statement in ANSWER_SEARCH_DDL:
        op.execute(statement)
    op.execute(ANSWER_SEARCH_BACKFILL)


def downgrade() -> None:
    for name in ("insert", "delete", "update"):
        op.execute(f"DROP TRIGGER tutor_answer_fts_{name}")
    op.execute("DROP TABLE tutor_answer_fts")
