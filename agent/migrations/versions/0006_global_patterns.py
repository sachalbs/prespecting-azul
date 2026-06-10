"""global_patterns: de-identified segment × hook_type × timing aggregates (empty)

No FK to prospects/tenants, no free-text column — categorical labels and
counters only. Created empty; nothing feeds it yet (the curator is a stub).
Defensive like 0002-0005 (0001 is a create_all of current models).

Revision ID: 0006
Revises: 0005
Create Date: 2026-06-10
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0006"
down_revision: str | None = "0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    bind = op.get_bind()
    if sa.inspect(bind).has_table("global_patterns"):
        return
    op.create_table(
        "global_patterns",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("segment", sa.String(120), nullable=False, index=True),
        sa.Column("hook_type", sa.String(32), nullable=False),
        sa.Column("send_dow", sa.Integer(), nullable=False),
        sa.Column("send_hour_bucket", sa.Integer(), nullable=False),
        sa.Column("n_sent", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("n_replied", sa.Integer(), nullable=False, server_default="0"),
        sa.UniqueConstraint(
            "segment", "hook_type", "send_dow", "send_hour_bucket", name="uq_global_pattern"
        ),
    )


def downgrade() -> None:
    op.drop_table("global_patterns")
