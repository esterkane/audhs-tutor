"""stage3 ingest: chunk norm_hash, provenance flags

Revision ID: cf384fbca033
Revises: 08e0e269a737
Create Date: 2026-09-19 16:00:38.727230

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "cf384fbca033"
down_revision: str | Sequence[str] | None = "08e0e269a737"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    with op.batch_alter_table("chunk", schema=None) as batch_op:
        batch_op.add_column(sa.Column("norm_hash", sa.Text(), nullable=True))
        batch_op.create_index(batch_op.f("ix_chunk_norm_hash"), ["norm_hash"], unique=False)

    with op.batch_alter_table("chunk_provenance", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column("flags_json", sa.JSON(), nullable=False, server_default=sa.text("'[]'"))
        )


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table("chunk_provenance", schema=None) as batch_op:
        batch_op.drop_column("flags_json")

    with op.batch_alter_table("chunk", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_chunk_norm_hash"))
        batch_op.drop_column("norm_hash")
