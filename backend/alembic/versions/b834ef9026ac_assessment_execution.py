"""Stage validated assessment results without inferring historical execution state."""

import sqlalchemy as sa

from alembic import op

revision = "b834ef9026ac"
down_revision = "a42e7f90d821"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "assessment_execution",
        sa.Column("claim_id", sa.Text(), primary_key=True),
        sa.Column("learner_id", sa.Text(), nullable=False),
        sa.Column("schema_version", sa.Integer(), nullable=False),
        sa.Column("phase", sa.Text(), nullable=False),
        sa.Column("content_fingerprint", sa.Text(), nullable=False),
        sa.Column("request_json", sa.JSON(), nullable=False),
        sa.Column("grade_json", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.Text(), nullable=False),
        sa.Column("updated_at", sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(["claim_id"], ["workspace_request.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["learner_id"], ["learner_profile.id"]),
    )
    op.create_index("ix_assessment_execution_learner_id", "assessment_execution", ["learner_id"])


def downgrade():
    op.drop_table("assessment_execution")
