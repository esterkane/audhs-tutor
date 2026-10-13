"""private lesson promotion storage

Revision ID: 30221b1ed8a7
Revises: c0ff66df480b
Create Date: 2026-10-13 14:12:19.721520

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op
from app.db.lesson_ddl import LESSON_IMMUTABLE_GUARDS

# revision identifiers, used by Alembic.
revision: str = "30221b1ed8a7"
down_revision: str | Sequence[str] | None = "c0ff66df480b"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_index("uq_curriculum_owned_id", "curriculum_draft", ["learner_id", "id"], unique=True)
    op.create_index("uq_answer_owned_id", "tutor_answer", ["learner_id", "id"], unique=True)
    op.create_table(
        "lesson_promotion",
        sa.Column("draft_id", sa.Text(), nullable=False),
        sa.Column("answer_id", sa.Text(), nullable=False),
        sa.Column("request_key", sa.Text(), nullable=False),
        sa.Column("fingerprint", sa.Text(), nullable=False),
        sa.Column("binding_json", sa.Text(), nullable=False),
        sa.Column("source_state_json", sa.Text(), nullable=False),
        sa.Column("created_at", sa.Text(), nullable=False),
        sa.Column("id", sa.Text(), nullable=False),
        sa.Column("learner_id", sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(
            ["learner_id", "answer_id"],
            ["tutor_answer.learner_id", "tutor_answer.id"],
            name="fk_lesson_promotion_owned_answer",
        ),
        sa.ForeignKeyConstraint(
            ["learner_id", "draft_id"],
            ["curriculum_draft.learner_id", "curriculum_draft.id"],
            name="fk_lesson_promotion_owned_draft",
        ),
        sa.ForeignKeyConstraint(
            ["learner_id"],
            ["learner_profile.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("draft_id", name="uq_lesson_promotion_draft"),
        sa.UniqueConstraint("learner_id", "id", name="uq_lesson_promotion_owned_id"),
        sa.UniqueConstraint("learner_id", "request_key", name="uq_lesson_promotion_request"),
    )
    with op.batch_alter_table("lesson_promotion", schema=None) as batch_op:
        batch_op.create_index(
            batch_op.f("ix_lesson_promotion_learner_id"), ["learner_id"], unique=False
        )

    op.create_table(
        "lesson_promotion_snapshot",
        sa.Column("promotion_id", sa.Text(), nullable=False),
        sa.Column("snapshot_json", sa.Text(), nullable=False),
        sa.Column("id", sa.Text(), nullable=False),
        sa.Column("learner_id", sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(
            ["learner_id", "promotion_id"],
            ["lesson_promotion.learner_id", "lesson_promotion.id"],
            name="fk_lesson_snapshot_owned_promotion",
        ),
        sa.ForeignKeyConstraint(
            ["learner_id"],
            ["learner_profile.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("promotion_id", name="uq_lesson_promotion_snapshot"),
    )
    with op.batch_alter_table("lesson_promotion_snapshot", schema=None) as batch_op:
        batch_op.create_index(
            batch_op.f("ix_lesson_promotion_snapshot_learner_id"), ["learner_id"], unique=False
        )

    for ddl in LESSON_IMMUTABLE_GUARDS.values():
        op.execute(ddl)


def downgrade() -> None:
    connection = op.get_bind()
    for table in LESSON_IMMUTABLE_GUARDS:
        if connection.execute(sa.text(f"SELECT count(*) FROM {table}")).scalar_one():
            raise RuntimeError("Cannot downgrade populated private lesson history")
    for table in reversed(LESSON_IMMUTABLE_GUARDS):
        op.execute(f"DROP TRIGGER IF EXISTS {table}_no_update")
    op.drop_table("lesson_promotion_snapshot")
    op.drop_table("lesson_promotion")
    op.drop_index("uq_answer_owned_id", table_name="tutor_answer")
    op.drop_index("uq_curriculum_owned_id", table_name="curriculum_draft")
