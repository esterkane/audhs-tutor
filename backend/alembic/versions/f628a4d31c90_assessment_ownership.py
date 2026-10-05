"""Optional assessment ownership evidence; legacy requests remain unknown."""

import sqlalchemy as sa

from alembic import op

revision = "f628a4d31c90"
down_revision = "e167bc2359df"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("assessment_execution", sa.Column("owner_json", sa.JSON(), nullable=True))


def downgrade():
    with op.batch_alter_table("assessment_execution") as batch:
        batch.drop_column("owner_json")
