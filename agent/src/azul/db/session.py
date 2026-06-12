"""Engine + session lifecycle."""

from __future__ import annotations

from collections.abc import Generator
from contextlib import contextmanager
from contextvars import ContextVar
from functools import lru_cache

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker

from azul.config import get_settings

# The session currently open via session_scope, if any. Side-channel writers
# (the API cost tracker) join this transaction instead of opening a competing
# one — sqlite allows a single writer.
_active_session: ContextVar[Session | None] = ContextVar("azul_active_session", default=None)


def active_session() -> Session | None:
    return _active_session.get()


@lru_cache(maxsize=1)
def get_engine() -> Engine:
    settings = get_settings()
    connect_args = {"check_same_thread": False} if settings.is_sqlite else {}
    return create_engine(settings.database_url, future=True, connect_args=connect_args)


@lru_cache(maxsize=1)
def get_sessionmaker() -> sessionmaker[Session]:
    return sessionmaker(bind=get_engine(), expire_on_commit=False, future=True)


@contextmanager
def session_scope() -> Generator[Session, None, None]:
    """Transactional scope: commit on success, roll back on error."""
    session = get_sessionmaker()()
    token = _active_session.set(session)
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        _active_session.reset(token)
        session.close()
