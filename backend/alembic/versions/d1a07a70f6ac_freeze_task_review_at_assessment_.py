"""freeze task review at assessment preparation

Revision ID: d1a07a70f6ac
Revises: 4ab714cf670c
Create Date: 2026-10-12 15:06:01.409616

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "d1a07a70f6ac"
down_revision: str | Sequence[str] | None = "4ab714cf670c"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("assessment_execution", sa.Column("task_review_json", sa.JSON(), nullable=True))


def downgrade() -> None:
    if (
        op.get_bind()
        .exec_driver_sql(
            "SELECT 1 FROM assessment_execution WHERE task_review_json IS NOT NULL LIMIT 1"
        )
        .first()
    ):
        raise RuntimeError("Cannot discard frozen task review history")
    with op.batch_alter_table("assessment_execution") as batch:
        batch.drop_column("task_review_json")
