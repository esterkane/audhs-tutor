"""stage3 dedupe: chunk duplicate_of, retrieval_trace reranker_id; backfill norm_hash + flags

Revision ID: 03c8da410c84
Revises: cf384fbca033
Create Date: 2026-09-19 16:35:27.032493

"""

import json
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "03c8da410c84"
down_revision: str | Sequence[str] | None = "cf384fbca033"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema, then backfill dedupe hashes and instruction flags on pre-Stage-3 chunks."""
    with op.batch_alter_table("chunk", schema=None) as batch_op:
        batch_op.add_column(sa.Column("duplicate_of", sa.Text(), nullable=True))
        batch_op.create_index(batch_op.f("ix_chunk_duplicate_of"), ["duplicate_of"], unique=False)
        batch_op.create_foreign_key("fk_chunk_duplicate_of", "chunk", ["duplicate_of"], ["id"])

    with op.batch_alter_table("retrieval_trace", schema=None) as batch_op:
        batch_op.add_column(sa.Column("reranker_id", sa.Text(), nullable=True))

    # data step: chunks ingested before Stage 3 have no norm_hash and empty flags
    from app.knowledge.ingest.normalize import norm_hash
    from app.knowledge.provenance import flag_instruction_patterns

    conn = op.get_bind()
    rows = conn.execute(sa.text("SELECT id, text FROM chunk WHERE norm_hash IS NULL")).all()
    for cid, text in rows:
        body = text.split("\n", 1)[1] if "\n" in text else text
        conn.execute(
            sa.text("UPDATE chunk SET norm_hash = :h WHERE id = :id"),
            {"h": norm_hash(body), "id": cid},
        )
        flags = flag_instruction_patterns(text)
        if flags:
            conn.execute(
                sa.text("UPDATE chunk_provenance SET flags_json = :f WHERE chunk_id = :id"),
                {"f": json.dumps(flags), "id": cid},
            )


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table("retrieval_trace", schema=None) as batch_op:
        batch_op.drop_column("reranker_id")

    with op.batch_alter_table("chunk", schema=None) as batch_op:
        batch_op.drop_constraint("fk_chunk_duplicate_of", type_="foreignkey")
        batch_op.drop_index(batch_op.f("ix_chunk_duplicate_of"))
        batch_op.drop_column("duplicate_of")
