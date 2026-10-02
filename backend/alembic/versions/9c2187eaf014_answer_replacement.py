"""Reviewed answer replacement preference."""

import sqlalchemy as sa

from alembic import op

revision = "9c2187eaf014"
down_revision = "55d7f6e0304b"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "tutor_answer_replacement",
        sa.Column("id", sa.Text(), nullable=False),
        sa.Column("learner_id", sa.Text(), nullable=False),
        sa.Column("answer_id", sa.Text(), nullable=False),
        sa.Column("replacement_id", sa.Text(), nullable=True),
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.Column("updated_at", sa.Text(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(
            ["learner_id"], ["learner_profile.id"], name="fk_replacement_learner"
        ),
        sa.ForeignKeyConstraint(["answer_id"], ["tutor_answer.id"], name="fk_replacement_original"),
        sa.ForeignKeyConstraint(
            ["replacement_id"], ["tutor_answer.id"], name="fk_replacement_target"
        ),
        sa.UniqueConstraint("learner_id", "answer_id", name="uq_answer_replacement_owner_answer"),
    )
    op.create_index(
        "ix_tutor_answer_replacement_learner_id", "tutor_answer_replacement", ["learner_id"]
    )
    op.create_index(
        "ix_tutor_answer_replacement_answer_id", "tutor_answer_replacement", ["answer_id"]
    )


def downgrade():
    op.drop_table("tutor_answer_replacement")
