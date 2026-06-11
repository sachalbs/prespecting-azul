"""messages: weak_hook flag (no strong signal — sober angle, review)

Defensive like 0002-0010 (0001 is a create_all of current models).

Revision ID: 0011
Revises: 0010
Create Date: 2026-06-10
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0011"
down_revision: str | None = "0010"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    bind = op.get_bind()
    cols = {c["name"] for c in sa.inspect(bind).get_columns("messages")}
    if "weak_hook" not in cols:
        op.add_column(
            "messages",
            sa.Column("weak_hook", sa.Boolean(), nullable=False, server_default=sa.false()),
        )


def downgrade() -> None:
    op.drop_column("messages", "weak_hook")
