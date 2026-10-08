"""Learner-owned question replacement lineage. Publication remains disabled."""

import sqlalchemy as sa

from alembic import op

revision = "a03d914ba627"
down_revision = "924acd018f31"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "question_replacement",
        sa.Column("learner_id", sa.Text(), sa.ForeignKey("learner_profile.id"), primary_key=True),
        sa.Column("original_id", sa.Text(), sa.ForeignKey("assessment.id"), primary_key=True),
        sa.Column("replacement_id", sa.Text(), sa.ForeignKey("assessment.id"), nullable=False),
        sa.Column("created_at", sa.Text(), nullable=False),
        sa.UniqueConstraint("learner_id", "replacement_id", name="uq_question_replacement_target"),
    )
    op.create_index(
        "ix_question_replacement_replacement_id", "question_replacement", ["replacement_id"]
    )


def downgrade():
    if op.get_bind().exec_driver_sql("SELECT 1 FROM question_replacement LIMIT 1").first():
        raise RuntimeError("Cannot downgrade while replacement lineage exists")
    op.drop_table("question_replacement")
