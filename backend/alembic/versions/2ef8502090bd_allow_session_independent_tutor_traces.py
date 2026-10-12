"""Allow session-independent tutor traces without fabricating learning sessions."""

import sqlalchemy as sa

from alembic import op

revision = "2ef8502090bd"
down_revision = "1b86eae1d303"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("tutor_trace") as batch:
        batch.alter_column("session_id", existing_type=sa.Text(), nullable=True)


def downgrade() -> None:
    if (
        op.get_bind()
        .execute(sa.text("SELECT count(*) FROM tutor_trace WHERE session_id IS NULL"))
        .scalar()
    ):
        raise RuntimeError("Cannot discard session-independent tutor traces")
    with op.batch_alter_table("tutor_trace") as batch:
        batch.alter_column("session_id", existing_type=sa.Text(), nullable=False)
