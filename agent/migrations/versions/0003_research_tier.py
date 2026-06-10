"""research: tier column (which tier of the staged router produced the hooks)

Defensive like 0002: migration 0001 create_all already materialises current
models on fresh databases, so only add the column when it is missing.

Revision ID: 0003
Revises: 0002
Create Date: 2026-06-10
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0003"
down_revision: str | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    bind = op.get_bind()
    cols = {c["name"] for c in sa.inspect(bind).get_columns("research")}
    if "tier" not in cols:
        op.add_column("research", sa.Column("tier", sa.String(20), nullable=True))


def downgrade() -> None:
    op.drop_column("research", "tier")
