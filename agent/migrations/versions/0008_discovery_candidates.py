"""discovery_candidates: discovered companies + annotations (nothing thrown away)

Defensive like 0002-0007 (0001 is a create_all of current models).

Revision ID: 0008
Revises: 0007
Create Date: 2026-06-10
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0008"
down_revision: str | None = "0007"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    bind = op.get_bind()
    if sa.inspect(bind).has_table("discovery_candidates"):
        return
    op.create_table(
        "discovery_candidates",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "tenant_id", sa.Uuid(), sa.ForeignKey("tenants.id"), nullable=False, index=True
        ),
        sa.Column("brief_id", sa.Uuid(), sa.ForeignKey("icp_briefs.id"), nullable=True),
        sa.Column("company_name", sa.String(200), nullable=False),
        sa.Column("domain", sa.String(255), nullable=False, index=True),
        sa.Column("founder_name", sa.String(200), nullable=True),
        sa.Column("founder_role", sa.String(200), nullable=True),
        sa.Column("source_url", sa.String(800), nullable=True),
        sa.Column("raw_context", sa.Text(), nullable=False),
        sa.Column("icp_score", sa.Float(), nullable=True),
        sa.Column("score_reason", sa.Text(), nullable=True),
        sa.Column("promoted", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("prospect_id", sa.Uuid(), sa.ForeignKey("prospects.id"), nullable=True),
        sa.UniqueConstraint("tenant_id", "domain", name="uq_candidate_tenant_domain"),
    )


def downgrade() -> None:
    op.drop_table("discovery_candidates")
