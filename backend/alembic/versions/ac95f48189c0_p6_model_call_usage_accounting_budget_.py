"""p6 model_call usage accounting, budget_reservation

Revision ID: ac95f48189c0
Revises: 367349aa228b
Create Date: 2026-09-20 16:34:15.523037

Every existing `model_call` row is stamped `usage_source='legacy'` (its tokens may be provider
counts or chars/4 estimates — the old rows did not say) and `cost_status='legacy'` for hosted rows /
`'free'` for local ones; `outcome` mirrors `ok`. New rows carry exact sources.
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "ac95f48189c0"
down_revision: str | Sequence[str] | None = "367349aa228b"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "budget_reservation",
        sa.Column("learner_id", sa.Text(), nullable=True),
        sa.Column("request_id", sa.Text(), nullable=False),
        sa.Column("registry_id", sa.Text(), nullable=False),
        sa.Column("task", sa.Text(), nullable=False),
        sa.Column("amount_usd", sa.Float(), nullable=False),
        sa.Column("status", sa.Text(), nullable=False, server_default="open"),
        sa.Column("settled_usd", sa.Float(), nullable=True),
        sa.Column("model_call_id", sa.Text(), nullable=True),
        sa.Column("created_at", sa.Text(), nullable=False),
        sa.Column("expires_at", sa.Text(), nullable=False),
        sa.Column("id", sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(
            ["learner_id"], ["learner_profile.id"], name="fk_budget_reservation_learner"
        ),
        sa.ForeignKeyConstraint(
            ["model_call_id"], ["model_call.id"], name="fk_budget_reservation_model_call"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table("budget_reservation", schema=None) as batch_op:
        batch_op.create_index("ix_budget_reservation_created_at", ["created_at"], unique=False)
        batch_op.create_index("ix_budget_reservation_expires_at", ["expires_at"], unique=False)
        batch_op.create_index("ix_budget_reservation_learner_id", ["learner_id"], unique=False)
        batch_op.create_index("ix_budget_reservation_request_id", ["request_id"], unique=False)

    with op.batch_alter_table("model_call", schema=None) as batch_op:
        batch_op.add_column(sa.Column("request_id", sa.Text(), nullable=True))
        batch_op.add_column(sa.Column("attempt", sa.Integer(), nullable=False, server_default="1"))
        batch_op.add_column(sa.Column("idempotency_key", sa.Text(), nullable=True))
        batch_op.add_column(sa.Column("outcome", sa.Text(), nullable=False, server_default="ok"))
        batch_op.add_column(
            sa.Column("usage_source", sa.Text(), nullable=False, server_default="legacy")
        )
        batch_op.add_column(
            sa.Column("cost_status", sa.Text(), nullable=False, server_default="legacy")
        )
        batch_op.add_column(
            sa.Column("reserved_usd", sa.Float(), nullable=False, server_default="0")
        )
        batch_op.create_index("ix_model_call_request_id", ["request_id"], unique=False)
        batch_op.create_unique_constraint("uq_model_call_idempotency_key", ["idempotency_key"])

    # data step: legacy rows are labelled as such, never given a precision they did not have
    conn = op.get_bind()
    conn.execute(sa.text("UPDATE model_call SET outcome = CASE WHEN ok THEN 'ok' ELSE 'error' END"))
    conn.execute(
        sa.text(
            "UPDATE model_call SET cost_status = CASE WHEN provider = 'anthropic' THEN 'legacy' "
            "ELSE 'free' END"
        )
    )


def downgrade() -> None:
    with op.batch_alter_table("model_call", schema=None) as batch_op:
        batch_op.drop_constraint("uq_model_call_idempotency_key", type_="unique")
        batch_op.drop_index("ix_model_call_request_id")
        batch_op.drop_column("reserved_usd")
        batch_op.drop_column("cost_status")
        batch_op.drop_column("usage_source")
        batch_op.drop_column("outcome")
        batch_op.drop_column("idempotency_key")
        batch_op.drop_column("attempt")
        batch_op.drop_column("request_id")

    with op.batch_alter_table("budget_reservation", schema=None) as batch_op:
        batch_op.drop_index("ix_budget_reservation_request_id")
        batch_op.drop_index("ix_budget_reservation_learner_id")
        batch_op.drop_index("ix_budget_reservation_expires_at")
        batch_op.drop_index("ix_budget_reservation_created_at")
    op.drop_table("budget_reservation")
