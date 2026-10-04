"""Immutable original browsing context; no inferred legacy backfill."""

import sqlalchemy as sa

from alembic import op

revision = "d056ab1248ce"
down_revision = "c945fa0137bd"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("parking_lot_item", sa.Column("original_context_json", sa.JSON(), nullable=True))


def downgrade():
    op.drop_column("parking_lot_item", "original_context_json")
