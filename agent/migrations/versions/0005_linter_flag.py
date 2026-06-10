"""messages: review_required flag (style linter gave up after 2 regenerations)

Defensive like 0002-0004 (0001 is a create_all of current models).

Revision ID: 0005
Revises: 0004
Create Date: 2026-06-10
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0005"
down_revision: str | None = "0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    bind = op.get_bind()
    cols = {c["name"] for c in sa.inspect(bind).get_columns("messages")}
    if "review_required" not in cols:
        op.add_column(
            "messages",
            sa.Column("review_required", sa.Boolean(), nullable=False, server_default=sa.false()),
        )


def downgrade() -> None:
    op.drop_column("messages", "review_required")
