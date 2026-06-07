"""Declarative base + portable column types.

JSON -> JSONB on Postgres. Vectors -> pgvector in prod, JSON on the SQLite
fallback (skills/embeddings are a flywheel concern, deferred past Jalon 0).
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from pgvector.sqlalchemy import Vector
from sqlalchemy import JSON, DateTime, Uuid
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

# JSONB where we can, plain JSON on sqlite.
JSONType = JSON().with_variant(JSONB(), "postgresql")


def vector_type(dim: int) -> Any:
    """pgvector column in prod, JSON blob on the sqlite fallback."""
    return Vector(dim).with_variant(JSON(), "sqlite")


class Base(DeclarativeBase):
    type_annotation_map = {
        dict[str, Any]: JSONType,
        list[dict[str, Any]]: JSONType,
        list[str]: JSONType,
        datetime: DateTime(timezone=True),
    }


class UUIDMixin:
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)


def _now() -> datetime:
    return datetime.now(tz=UTC)


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(default=_now)
    updated_at: Mapped[datetime] = mapped_column(default=_now, onupdate=_now)
