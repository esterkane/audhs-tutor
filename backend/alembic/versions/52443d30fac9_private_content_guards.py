"""Enforce private curriculum ownership without rewriting legacy data."""

from alembic import op
from app.db.content_ddl import CONTENT_GUARDS, INVALID_ASSESSMENT, INVALID_EDGE

revision = "52443d30fac9"
down_revision = "41332c2fe9b8"
branch_labels = None
depends_on = None


def upgrade():
    for query in (INVALID_EDGE, INVALID_ASSESSMENT):
        if op.get_bind().exec_driver_sql(query).first():
            raise RuntimeError("Invalid private content relationships; migration refused")
    for ddl in CONTENT_GUARDS.values():
        op.execute(ddl)


def downgrade():
    for table in ("skill_node", "assessment"):
        if (
            op.get_bind()
            .exec_driver_sql(f"SELECT 1 FROM {table} WHERE owner_learner_id IS NOT NULL LIMIT 1")
            .first()
        ):
            label = "skills" if table == "skill_node" else "assessments"
            raise RuntimeError(f"Cannot downgrade while private {label} exist")
    for name in CONTENT_GUARDS:
        op.execute(f"DROP TRIGGER IF EXISTS {name}")
