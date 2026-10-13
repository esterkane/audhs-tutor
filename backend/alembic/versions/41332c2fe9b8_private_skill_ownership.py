"""Private skill ownership foundation; existing nodes remain shared."""

from alembic import op

revision = "41332c2fe9b8"
down_revision = "30221b1ed8a7"
branch_labels = None
depends_on = None


def upgrade():
    op.execute(
        "ALTER TABLE skill_node ADD COLUMN owner_learner_id TEXT "
        "REFERENCES learner_profile(id) ON DELETE RESTRICT"
    )
    op.create_index("ix_skill_node_owner_learner_id", "skill_node", ["owner_learner_id"])


def downgrade():
    if (
        op.get_bind()
        .exec_driver_sql("SELECT 1 FROM skill_node WHERE owner_learner_id IS NOT NULL LIMIT 1")
        .first()
    ):
        raise RuntimeError("Cannot downgrade while private skills exist")
    op.drop_index("ix_skill_node_owner_learner_id", table_name="skill_node")
    op.execute("ALTER TABLE skill_node DROP COLUMN owner_learner_id")
