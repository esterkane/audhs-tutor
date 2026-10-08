"""Private assessment visibility; existing content remains shared."""

from alembic import op

revision = "924acd018f31"
down_revision = "773f25ae3e92"
branch_labels = None
depends_on = None


def upgrade():
    # SQLite supports nullable REFERENCES additions without rebuilding referenced tables.
    op.execute(
        "ALTER TABLE assessment ADD COLUMN owner_learner_id TEXT "
        "REFERENCES learner_profile(id) ON DELETE RESTRICT"
    )
    op.create_index("ix_assessment_owner_learner_id", "assessment", ["owner_learner_id"])


def downgrade():
    if (
        op.get_bind()
        .exec_driver_sql("SELECT 1 FROM assessment WHERE owner_learner_id IS NOT NULL LIMIT 1")
        .first()
    ):
        raise RuntimeError("Cannot downgrade while private assessments exist")
    op.drop_index("ix_assessment_owner_learner_id", table_name="assessment")
    op.execute("ALTER TABLE assessment DROP COLUMN owner_learner_id")
