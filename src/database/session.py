"""Centralized session factory helpers for project and catalog databases.

Use these helpers to avoid ad-hoc session construction and keep initialization
consistent across services, controllers, and background tasks.
"""

from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path
from typing import Callable, Iterator

from sqlalchemy.orm import Session

from .base import get_project_session, init_project_db
from .catalog_base import get_catalog_session, init_catalog_db

SessionFactory = Callable[[], Session]


def project_session_factory(db_path: Path) -> SessionFactory:
    """Return a session factory bound to a specific project database."""

    def _factory() -> Session:
        init_project_db(db_path)
        return get_project_session(db_path)

    return _factory


def catalog_session_factory() -> SessionFactory:
    """Return a session factory for the catalog database."""

    def _factory() -> Session:
        init_catalog_db()
        return get_catalog_session()

    return _factory


@contextmanager
def session_scope(factory: SessionFactory) -> Iterator[Session]:
    """Context manager for commit/rollback semantics around a session factory."""
    session = factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
