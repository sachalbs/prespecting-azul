"""messages: hook_type taxonomy + subject_len/word_count (learning schema)

Human-edit capture needs no new column: the original draft stays in `body`,
the human version in `human_edited_body` (set with review_decision=EDIT), so the
unified diff is derivable. Defensive like 0002/0003 (0001 is a create_all).

Revision ID: 0004
Revises: 0003
Create Date: 2026-06-10
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0004"
down_revision: str | None = "0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    bind = op.get_bind()
    cols = {c["name"] for c in sa.inspect(bind).get_columns("messages")}
    if "hook_type" not in cols:
        op.add_column("messages", sa.Column("hook_type", sa.String(32), nullable=True))
    if "subject_len" not in cols:
        op.add_column("messages", sa.Column("subject_len", sa.Integer(), nullable=True))
    if "word_count" not in cols:
        op.add_column("messages", sa.Column("word_count", sa.Integer(), nullable=True))


def downgrade() -> None:
    op.drop_column("messages", "word_count")
    op.drop_column("messages", "subject_len")
    op.drop_column("messages", "hook_type")
