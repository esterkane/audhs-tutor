"""Durable learner-scoped thought save identity; legacy saves stay unkeyed."""

import sqlalchemy as sa

from alembic import op

revision = "c945fa0137bd"
down_revision = "b834ef9026ac"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("parking_lot_item", sa.Column("request_key", sa.Text(), nullable=True))
    op.add_column("parking_lot_item", sa.Column("request_fingerprint", sa.Text(), nullable=True))
    op.create_index(
        "uq_parking_owner_request", "parking_lot_item", ["learner_id", "request_key"], unique=True
    )


def downgrade():
    op.drop_index("uq_parking_owner_request", table_name="parking_lot_item")
    op.drop_column("parking_lot_item", "request_fingerprint")
    op.drop_column("parking_lot_item", "request_key")
