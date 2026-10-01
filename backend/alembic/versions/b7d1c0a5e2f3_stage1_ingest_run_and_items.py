"""course-material stage 1: ingest_run + ingest_run_item (progress, outcomes, resume)

Revision ID: b7d1c0a5e2f3
Revises: e3ee9810831b
Create Date: 2026-09-21 16:10:00

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b7d1c0a5e2f3"
down_revision: str | Sequence[str] | None = "e3ee9810831b"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "ingest_run",
        sa.Column("id", sa.Text(), nullable=False),
        sa.Column("src", sa.Text(), nullable=False),
        sa.Column("course", sa.Text(), nullable=True),
        sa.Column("options_json", sa.JSON(), nullable=False),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("started_at", sa.Text(), nullable=False),
        sa.Column("finished_at", sa.Text(), nullable=True),
        sa.Column("files_total", sa.Integer(), nullable=False),
        sa.Column("files_done", sa.Integer(), nullable=False),
        sa.Column("last_uri", sa.Text(), nullable=True),
        sa.Column("resumed_from", sa.Text(), nullable=True),
        sa.Column("summary_json", sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(["resumed_from"], ["ingest_run.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table("ingest_run", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_ingest_run_src"), ["src"], unique=False)
        batch_op.create_index(batch_op.f("ix_ingest_run_status"), ["status"], unique=False)
    op.create_table(
        "ingest_run_item",
        sa.Column("id", sa.Text(), nullable=False),
        sa.Column("run_id", sa.Text(), nullable=False),
        sa.Column("uri", sa.Text(), nullable=False),
        sa.Column("outcome", sa.Text(), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("document_id", sa.Text(), nullable=True),
        sa.Column("version_id", sa.Text(), nullable=True),
        sa.Column("ts", sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(["run_id"], ["ingest_run.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("run_id", "uri", name="uq_ingest_run_item_run_uri"),
    )
    with op.batch_alter_table("ingest_run_item", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_ingest_run_item_run_id"), ["run_id"], unique=False)
        batch_op.create_index(batch_op.f("ix_ingest_run_item_outcome"), ["outcome"], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table("ingest_run_item", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_ingest_run_item_outcome"))
        batch_op.drop_index(batch_op.f("ix_ingest_run_item_run_id"))
    op.drop_table("ingest_run_item")
    with op.batch_alter_table("ingest_run", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_ingest_run_status"))
        batch_op.drop_index(batch_op.f("ix_ingest_run_src"))
    op.drop_table("ingest_run")
