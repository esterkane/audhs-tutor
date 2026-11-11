"""Explicitly saved predictions and delayed, ungraded recall."""

import sqlalchemy as sa

from alembic import op

revision = "d91af472c30b"
down_revision = "c8e5a1f03972"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "reading_prediction",
        sa.Column("id", sa.Text(), primary_key=True),
        sa.Column("learner_id", sa.Text(), sa.ForeignKey("learner_profile.id"), nullable=False),
        sa.Column("draft_id", sa.Text(), sa.ForeignKey("curriculum_draft.id"), nullable=False),
        sa.Column("object_id", sa.Text(), sa.ForeignKey("learning_object.id"), nullable=False),
        sa.Column("learning_object_version", sa.Integer(), nullable=False),
        *(
            sa.Column(name, sa.Text(), nullable=False)
            for name in (
                "question_id",
                "target",
                "content_sha256",
                "title",
                "question",
                "passage",
                "prediction",
                "created_at",
                "due_at",
            )
        ),
        sa.Column("answer", sa.Text(), nullable=True),
        sa.Column("answered_at", sa.Text(), nullable=True),
        sa.UniqueConstraint(
            "learner_id",
            "draft_id",
            "learning_object_version",
            "question_id",
            name="uq_reading_prediction_binding",
        ),
    )
    op.create_index("ix_reading_prediction_learner_id", "reading_prediction", ["learner_id"])
    op.create_index(
        "ix_reading_prediction_due", "reading_prediction", ["learner_id", "answered_at", "due_at"]
    )


def downgrade() -> None:
    bind = op.get_bind()
    if bind.exec_driver_sql("SELECT 1 FROM reading_prediction LIMIT 1").first():
        raise RuntimeError("Cannot downgrade populated reading prediction history")
    op.drop_table("reading_prediction")
