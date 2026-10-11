"""Retain content identity and original-attempt relationship for revised practice."""

import sqlalchemy as sa

from alembic import op

revision = "d257a941be03"
down_revision = "c146f830ad92"
branch_labels = None
depends_on = None


def upgrade():
    # Nullable additions preserve old evidence without claiming a historical version.
    op.add_column("assessment_attempt", sa.Column("content_fingerprint", sa.Text(), nullable=True))
    # SQLite supports a nullable REFERENCES column without rebuilding referenced tables.
    op.execute(
        "ALTER TABLE assessment_attempt ADD COLUMN revision_of_attempt_id TEXT "
        "REFERENCES assessment_attempt(id)"
    )
    op.create_index(
        "ix_assessment_attempt_revision_of_attempt_id",
        "assessment_attempt",
        ["revision_of_attempt_id"],
    )


def downgrade():
    if (
        op.get_bind()
        .exec_driver_sql(
            "SELECT 1 FROM assessment_attempt WHERE revision_of_attempt_id IS NOT NULL LIMIT 1"
        )
        .first()
    ):
        raise RuntimeError("Cannot discard recorded assessment revision relationships")
    op.drop_index("ix_assessment_attempt_revision_of_attempt_id", table_name="assessment_attempt")
    op.drop_column("assessment_attempt", "revision_of_attempt_id")
    op.drop_column("assessment_attempt", "content_fingerprint")
