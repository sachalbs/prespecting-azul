"""messages: conversation_id (Graph thread id) so sync-replies matches by thread

Defensive like 0002-0011 (0001 is a create_all of current models).

Revision ID: 0012
Revises: 0011
Create Date: 2026-06-12
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0012"
down_revision: str | None = "0011"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    bind = op.get_bind()
    cols = {c["name"] for c in sa.inspect(bind).get_columns("messages")}
    if "conversation_id" not in cols:
        op.add_column(
            "messages", sa.Column("conversation_id", sa.String(length=255), nullable=True)
        )
        op.create_index(
            "ix_messages_conversation_id", "messages", ["conversation_id"]
        )


def downgrade() -> None:
    op.drop_index("ix_messages_conversation_id", table_name="messages")
    op.drop_column("messages", "conversation_id")
