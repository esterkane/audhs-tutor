"""course-material stage 3: skill_node.section + order_no (course order for the next-skill pick)

Revision ID: d4a7b2c9e1f0
Revises: c8e2f1a9b4d0
Create Date: 2026-09-23 10:00:00

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "d4a7b2c9e1f0"
down_revision: str | Sequence[str] | None = "c8e2f1a9b4d0"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    with op.batch_alter_table("skill_node", schema=None) as batch_op:
        batch_op.add_column(sa.Column("section", sa.Text(), nullable=True))
        batch_op.add_column(sa.Column("order_no", sa.Integer(), nullable=True))
        batch_op.create_index(batch_op.f("ix_skill_node_order_no"), ["order_no"], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table("skill_node", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_skill_node_order_no"))
        batch_op.drop_column("order_no")
        batch_op.drop_column("section")
