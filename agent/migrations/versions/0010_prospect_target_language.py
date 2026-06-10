"""prospects: inferred outreach language (computed once, reused on redraft)

Defensive like 0002-0009 (0001 is a create_all of current models).

Revision ID: 0010
Revises: 0009
Create Date: 2026-06-10
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0010"
down_revision: str | None = "0009"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    bind = op.get_bind()
    cols = {c["name"] for c in sa.inspect(bind).get_columns("prospects")}
    if "target_language" not in cols:
        op.add_column("prospects", sa.Column("target_language", sa.String(8), nullable=True))


def downgrade() -> None:
    op.drop_column("prospects", "target_language")
