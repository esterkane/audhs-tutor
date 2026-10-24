"""Scheduled, version-bound factual review history."""

import sqlalchemy as sa

from alembic import op

revision = "b7c4f0a2d681"
down_revision = "a71f2039c4de"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "knowledge_review",
        sa.Column("id", sa.Text(), primary_key=True),
        sa.Column("learner_id", sa.Text(), sa.ForeignKey("learner_profile.id"), nullable=False),
        sa.Column("draft_id", sa.Text(), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.Column("interval_days", sa.Integer(), nullable=False),
        sa.Column("urls_json", sa.JSON(), nullable=False),
        sa.Column("next_due_at", sa.Text(), nullable=False),
        sa.Column("running_until", sa.Text(), nullable=True),
        sa.Column("history_json", sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(
            ["learner_id", "draft_id"], ["curriculum_draft.learner_id", "curriculum_draft.id"]
        ),
        sa.UniqueConstraint("learner_id", "draft_id", name="uq_knowledge_review_draft"),
        sa.CheckConstraint(
            "interval_days >= 1 AND interval_days <= 365", name="ck_knowledge_review_interval"
        ),
    )
    op.create_index("ix_knowledge_review_learner_id", "knowledge_review", ["learner_id"])
    op.create_index("ix_knowledge_review_due", "knowledge_review", ["enabled", "next_due_at"])


def downgrade() -> None:
    # SQLite DDL is not transactional: preflight later history guards before dropping anything.
    bind = op.get_bind()
    if bind.exec_driver_sql("SELECT 1 FROM provisional_feedback LIMIT 1").first():
        raise RuntimeError("Cannot downgrade populated provisional feedback history")
    if bind.exec_driver_sql("SELECT 1 FROM knowledge_review LIMIT 1").first():
        raise RuntimeError("Cannot downgrade populated factual review history")
    op.drop_table("knowledge_review")
