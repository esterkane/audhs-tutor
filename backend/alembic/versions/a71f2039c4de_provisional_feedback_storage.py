"""Separate learner-owned provisional model feedback storage.

Revision ID: a71f2039c4de
Revises: 969f9ebbe38a
"""

import sqlalchemy as sa

from alembic import op
from app.db.provisional_ddl import PROVISIONAL_GUARDS

revision = "a71f2039c4de"
down_revision = "969f9ebbe38a"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "provisional_feedback",
        sa.Column("id", sa.Text(), primary_key=True),
        sa.Column("learner_id", sa.Text(), sa.ForeignKey("learner_profile.id"), nullable=False),
        sa.Column("claim_id", sa.Text(), sa.ForeignKey("workspace_request.id"), nullable=False),
        sa.Column("session_id", sa.Text(), sa.ForeignKey("session.id"), nullable=False),
        sa.Column("assessment_id", sa.Text(), sa.ForeignKey("assessment.id"), nullable=False),
        sa.Column("revision_of_feedback_id", sa.Text(), sa.ForeignKey("provisional_feedback.id")),
        sa.Column("policy_version", sa.Text(), nullable=False),
        sa.Column("content_fingerprint", sa.Text(), nullable=False),
        sa.Column("answer", sa.Text(), nullable=False),
        sa.Column("binding_json", sa.JSON(), nullable=False),
        sa.Column("model_output_json", sa.JSON(), nullable=False),
        sa.Column("outcome_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.Text(), nullable=False),
        sa.UniqueConstraint("claim_id", name="uq_provisional_feedback_claim"),
    )
    op.create_index("ix_provisional_feedback_learner_id", "provisional_feedback", ["learner_id"])
    for ddl in PROVISIONAL_GUARDS.values():
        op.execute(ddl)


def downgrade() -> None:
    if op.get_bind().exec_driver_sql("SELECT 1 FROM provisional_feedback LIMIT 1").first():
        raise RuntimeError("Cannot downgrade populated provisional feedback history")
    for name in PROVISIONAL_GUARDS:
        op.execute(f"DROP TRIGGER IF EXISTS {name}")
    op.drop_table("provisional_feedback")
