"""Test config: sqlite temp DB + stub adapters, set before importing the app."""

from __future__ import annotations

import os
import tempfile
from collections.abc import Iterator
from pathlib import Path

_TMP = Path(tempfile.mkdtemp())
os.environ.setdefault("DATABASE_URL", f"sqlite:///{_TMP / 'test.db'}")
os.environ.setdefault("SOURCING_PROVIDER", "stub")
os.environ.setdefault("RESEARCH_ENGINE", "stub")
os.environ.setdefault("WRITER_PROVIDER", "stub")
os.environ.setdefault("CHANNEL", "stub")

import pytest  # noqa: E402

from azul.db import Base, get_engine  # noqa: E402  (importing azul.db registers mappers)


@pytest.fixture(autouse=True)
def schema() -> Iterator[None]:
    engine = get_engine()
    Base.metadata.create_all(engine)
    yield
    Base.metadata.drop_all(engine)
