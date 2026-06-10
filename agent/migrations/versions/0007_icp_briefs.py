"""icp_briefs: the tenant's conversational targeting memory

Defensive like 0002-0006 (0001 is a create_all of current models).

Revision ID: 0007
Revises: 0006
Create Date: 2026-06-10
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0007"
down_revision: str | None = "0006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    bind = op.get_bind()
    if sa.inspect(bind).has_table("icp_briefs"):
        return
    op.create_table(
        "icp_briefs",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "tenant_id", sa.Uuid(), sa.ForeignKey("tenants.id"), nullable=False, index=True
        ),
        sa.Column("raw_text", sa.Text(), nullable=False),
        sa.Column("sells", sa.String(400), nullable=True),
        sa.Column("sector", sa.String(200), nullable=True),
        sa.Column("company_size", sa.String(120), nullable=True),
        sa.Column("geo", sa.String(200), nullable=True),
        sa.Column("target_role", sa.String(200), nullable=True),
        sa.Column("good_prospect", sa.Text(), nullable=True),
        sa.Column("pain_signals", sa.JSON(), nullable=False),
        sa.Column("tone", sa.String(200), nullable=True),
    )


def downgrade() -> None:
    op.drop_table("icp_briefs")
