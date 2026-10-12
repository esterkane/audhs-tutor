"""explicit task review receipts

Revision ID: 4ab714cf670c
Revises: d257a941be03
Create Date: 2026-10-12 14:35:33.337481

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "4ab714cf670c"
down_revision: str | Sequence[str] | None = "d257a941be03"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "assessment_task_review",
        sa.Column("assessment_id", sa.Text(), nullable=False),
        sa.Column("request_id", sa.Text(), nullable=False),
        sa.Column("request_json", sa.JSON(), nullable=False),
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.Column("decision", sa.Text(), nullable=False),
        sa.Column("facet", sa.Text(), nullable=False),
        sa.Column("content_json", sa.JSON(), nullable=False),
        sa.Column("content_fingerprint", sa.Text(), nullable=False),
        sa.Column("policy_version", sa.Text(), nullable=False),
        sa.Column("reviewed_at", sa.Text(), nullable=False),
        sa.Column("id", sa.Text(), nullable=False),
        sa.Column("learner_id", sa.Text(), nullable=False),
        sa.CheckConstraint("decision IN ('approve', 'revoke')", name="ck_task_review_decision"),
        sa.CheckConstraint("facet IN ('explanation', 'application')", name="ck_task_review_facet"),
        sa.CheckConstraint("revision >= 1", name="ck_task_review_revision"),
        sa.ForeignKeyConstraint(
            ["assessment_id"], ["assessment.id"], name="fk_task_review_assessment"
        ),
        sa.ForeignKeyConstraint(
            ["learner_id"], ["learner_profile.id"], name="fk_task_review_learner"
        ),
        sa.PrimaryKeyConstraint("id", name="pk_assessment_task_review"),
        sa.UniqueConstraint(
            "learner_id", "assessment_id", "revision", name="uq_task_review_revision"
        ),
        sa.UniqueConstraint("learner_id", "request_id", name="uq_task_review_request"),
    )
    with op.batch_alter_table("assessment_task_review", schema=None) as batch_op:
        batch_op.create_index(
            batch_op.f("ix_assessment_task_review_assessment_id"), ["assessment_id"], unique=False
        )
        batch_op.create_index(
            batch_op.f("ix_assessment_task_review_learner_id"), ["learner_id"], unique=False
        )


def downgrade() -> None:
    if op.get_bind().exec_driver_sql("SELECT 1 FROM assessment_task_review LIMIT 1").first():
        raise RuntimeError("Cannot discard recorded task reviews")
    op.drop_table("assessment_task_review")
