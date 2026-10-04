"""Revisioned reminder actions and durable undo receipts."""

import sqlalchemy as sa

from alembic import op

revision = "e167bc2359df"
down_revision = "d056ab1248ce"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "parking_lot_item", sa.Column("revision", sa.Integer(), nullable=False, server_default="0")
    )
    op.create_table(
        "thought_action",
        sa.Column("id", sa.Text(), primary_key=True),
        sa.Column("learner_id", sa.Text(), sa.ForeignKey("learner_profile.id"), nullable=False),
        sa.Column("item_id", sa.Text(), sa.ForeignKey("parking_lot_item.id"), nullable=False),
        sa.Column("request_key", sa.Text(), nullable=False),
        sa.Column("fingerprint", sa.Text(), nullable=False),
        sa.Column("action", sa.Text(), nullable=False),
        sa.Column("before_json", sa.JSON(), nullable=False),
        sa.Column("after_json", sa.JSON(), nullable=False),
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.Column("undo_of", sa.Text(), nullable=True),
        sa.Column("created_at", sa.Text(), nullable=False),
        sa.UniqueConstraint("learner_id", "request_key"),
    )
    op.create_index("ix_thought_action_learner_id", "thought_action", ["learner_id"])


def downgrade():
    op.drop_table("thought_action")
    op.drop_column("parking_lot_item", "revision")
