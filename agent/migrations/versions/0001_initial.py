"""initial schema (Jalon 0 + flywheel-ready tables)

Baseline migration: materialises the current models and enables pgvector on
Postgres. Subsequent schema changes use `alembic revision --autogenerate`.

Revision ID: 0001
Revises:
Create Date: 2026-06-07
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

from azul.db import models  # noqa: F401  (register mappers)
from azul.db.base import Base

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    Base.metadata.create_all(bind)


def downgrade() -> None:
    Base.metadata.drop_all(op.get_bind())
