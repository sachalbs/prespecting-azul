"""prospects: verify_status + verify_confidence (in-house verifier verdict)

Defensive: migration 0001 materialises the *current* models via create_all, so a
fresh database already has these columns — only add them when they are missing
(existing databases created before this revision).

Revision ID: 0002
Revises: 0001
Create Date: 2026-06-10
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    bind = op.get_bind()
    cols = {c["name"] for c in sa.inspect(bind).get_columns("prospects")}
    if "verify_status" not in cols:
        op.add_column("prospects", sa.Column("verify_status", sa.String(32), nullable=True))
    if "verify_confidence" not in cols:
        op.add_column("prospects", sa.Column("verify_confidence", sa.Float(), nullable=True))


def downgrade() -> None:
    op.drop_column("prospects", "verify_confidence")
    op.drop_column("prospects", "verify_status")
