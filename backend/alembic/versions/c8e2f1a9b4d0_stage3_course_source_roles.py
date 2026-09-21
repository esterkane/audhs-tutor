"""course-material stage 3: course_source (owner-decided source roles for drafting)

Revision ID: c8e2f1a9b4d0
Revises: b7d1c0a5e2f3
Create Date: 2026-09-21 18:30:00

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c8e2f1a9b4d0"
down_revision: str | Sequence[str] | None = "b7d1c0a5e2f3"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "course_source",
        sa.Column("id", sa.Text(), nullable=False),
        sa.Column("course", sa.Text(), nullable=False),
        sa.Column("document_id", sa.Text(), nullable=False),
        sa.Column("role", sa.Text(), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("decided_by", sa.Text(), nullable=False),
        sa.Column("decided_at", sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(["document_id"], ["document.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("document_id", name="uq_course_source_document"),
    )
    with op.batch_alter_table("course_source", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_course_source_course"), ["course"], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table("course_source", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_course_source_course"))
    op.drop_table("course_source")
