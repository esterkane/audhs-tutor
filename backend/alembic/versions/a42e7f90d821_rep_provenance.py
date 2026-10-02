"""Preserve representation source snapshots across cache hits."""

import sqlalchemy as sa

from alembic import op

revision = "a42e7f90d821"
down_revision = "9c2187eaf014"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "representation",
        sa.Column("provenance_json", sa.JSON(), server_default=sa.text("'{}'"), nullable=False),
    )


def downgrade():
    with op.batch_alter_table("representation") as batch:
        batch.drop_column("provenance_json")
