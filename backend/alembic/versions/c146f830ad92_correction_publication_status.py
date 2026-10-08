"""Allow explicit correction publication; preserve all prior command receipts."""

from alembic import op

revision = "c146f830ad92"
down_revision = "a03d914ba627"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("question_correction_draft") as batch:
        batch.drop_constraint("ck_correction_draft_status", type_="check")
        batch.create_check_constraint(
            "ck_correction_draft_status", "status IN ('draft', 'discarded', 'published')"
        )


def downgrade():
    if (
        op.get_bind()
        .exec_driver_sql("SELECT 1 FROM question_correction_draft WHERE status='published' LIMIT 1")
        .first()
    ):
        raise RuntimeError("Cannot downgrade while published correction drafts exist")
    with op.batch_alter_table("question_correction_draft") as batch:
        batch.drop_constraint("ck_correction_draft_status", type_="check")
        batch.create_check_constraint(
            "ck_correction_draft_status", "status IN ('draft', 'discarded')"
        )
