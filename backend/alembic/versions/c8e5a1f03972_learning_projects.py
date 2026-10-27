"""Learner-owned knowledge testing projects, independent from mastery."""

import sqlalchemy as sa

from alembic import op

revision = "c8e5a1f03972"
down_revision = "b7c4f0a2d681"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "learning_project",
        sa.Column("id", sa.Text(), primary_key=True),
        sa.Column("learner_id", sa.Text(), sa.ForeignKey("learner_profile.id"), nullable=False),
        sa.Column("slug", sa.Text(), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("topic", sa.Text(), nullable=False),
        sa.Column("objective", sa.Text(), nullable=False),
        sa.Column("brief_json", sa.JSON(), nullable=False),
        sa.Column("notes", sa.Text(), nullable=False),
        sa.Column("evidence", sa.Text(), nullable=False),
        sa.Column("reflection", sa.Text(), nullable=False),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.Text(), nullable=False),
        sa.Column("updated_at", sa.Text(), nullable=False),
        sa.UniqueConstraint("learner_id", "slug", name="uq_learning_project_owner_slug"),
    )
    op.create_index("ix_learning_project_learner_id", "learning_project", ["learner_id"])


def downgrade() -> None:
    # SQLite DDL is not transactional: preflight every downstream history guard first.
    bind = op.get_bind()
    for table, label in [
        ("provisional_feedback", "provisional feedback"),
        ("knowledge_review", "factual review"),
        ("learning_project", "project writing"),
    ]:
        if bind.exec_driver_sql("SELECT 1 FROM " + table + " LIMIT 1").first():
            raise RuntimeError("Cannot downgrade populated " + label + " history")
    op.drop_table("learning_project")
