"""prospects: explicit first_name / last_name (verified order)

Defensive like 0002-0008 (0001 is a create_all of current models).

Revision ID: 0009
Revises: 0008
Create Date: 2026-06-10
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0009"
down_revision: str | None = "0008"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    bind = op.get_bind()
    cols = {c["name"] for c in sa.inspect(bind).get_columns("prospects")}
    if "first_name" not in cols:
        op.add_column("prospects", sa.Column("first_name", sa.String(120), nullable=True))
    if "last_name" not in cols:
        op.add_column("prospects", sa.Column("last_name", sa.String(120), nullable=True))


def downgrade() -> None:
    op.drop_column("prospects", "last_name")
    op.drop_column("prospects", "first_name")
