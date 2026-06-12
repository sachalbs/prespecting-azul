"""api_calls: per-call cost log (what a prospect costs us)

Defensive like 0002-0012 (0001 is a create_all of current models).

Revision ID: 0013
Revises: 0012
Create Date: 2026-06-12
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0013"
down_revision: str | None = "0012"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    bind = op.get_bind()
    if sa.inspect(bind).has_table("api_calls"):
        return
    op.create_table(
        "api_calls",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("service", sa.String(length=40), nullable=False),
        sa.Column("operation", sa.String(length=60), nullable=False),
        sa.Column("campaign_id", sa.Uuid(), sa.ForeignKey("campaigns.id"), nullable=True),
        sa.Column("prospect_id", sa.Uuid(), sa.ForeignKey("prospects.id"), nullable=True),
        sa.Column("prospect_label", sa.String(length=320), nullable=True),
        sa.Column("calls", sa.Integer(), nullable=False),
        sa.Column("tokens_in", sa.Integer(), nullable=False),
        sa.Column("tokens_out", sa.Integer(), nullable=False),
        sa.Column("cost_usd", sa.Float(), nullable=False),
    )
    op.create_index("ix_api_calls_service", "api_calls", ["service"])
    op.create_index("ix_api_calls_campaign_id", "api_calls", ["campaign_id"])
    op.create_index("ix_api_calls_prospect_id", "api_calls", ["prospect_id"])


def downgrade() -> None:
    op.drop_table("api_calls")
