"""Centralized session factory helpers for project and catalog databases.

This is the CANONICAL source for all session and engine management.
Import session-related functions from here, not from base.py or catalog_base.py.

Use these helpers to avoid ad-hoc session construction and keep initialization
consistent across services, controllers, and background tasks.

Thread Safety:
    SQLAlchemy sessions are NOT thread-safe. When using sessions in QThread workers
    or other background threads, always use `thread_scoped_session` or create a new
    session via the factory - never share a session across threads.

Usage:
    # For project databases:
    from database.session import project_session_factory, thread_scoped_session

    # Create a factory for repeated use:
    factory = project_session_factory(db_path)
    session = factory()

    # For one-off operations in worker threads:
    with thread_scoped_session(db_path) as session:
        # ... do work ...

    # For catalog database:
    from database.session import catalog_session_scope
    with catalog_session_scope() as session:
        # ... do work ...
"""

from __future__ import annotations

import logging
from contextlib import contextmanager
from pathlib import Path
from typing import Callable, Iterator, Union

from sqlalchemy.orm import Session

# Import from internal modules - these are the actual implementations
from .base import (
    get_project_session,
    init_project_db,
    get_project_db_path,
    dispose_project_engine,
    dispose_all_engines,
    PROJECTS_DIR,
    DATA_DIR,
)
from .catalog_base import (
    get_catalog_session,
    init_catalog_db,
    CATALOG_DB_PATH,
)

logger = logging.getLogger(__name__)

SessionFactory = Callable[[], Session]

# Re-export commonly used items for single-source imports
__all__ = [
    # Session factories
    "SessionFactory",
    "project_session_factory",
    "catalog_session_factory",
    # Context managers
    "session_scope",
    "thread_scoped_session",
    "catalog_session_scope",
    # Project database
    "get_project_session",
    "init_project_db",
    "get_project_db_path",
    "dispose_project_engine",
    "dispose_all_engines",
    "PROJECTS_DIR",
    "DATA_DIR",
    # Catalog database
    "get_catalog_session",
    "init_catalog_db",
    "CATALOG_DB_PATH",
]


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


@contextmanager
def catalog_session_scope() -> Iterator[Session]:
    """Context manager for catalog database operations.

    Usage:
        with catalog_session_scope() as session:
            repo = CatalogProjectRepository(session)
            projects = repo.get_all()
    """
    init_catalog_db()
    session = get_catalog_session()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


@contextmanager
def thread_scoped_session(db_path: Union[Path, str]) -> Iterator[Session]:
    """Create a thread-safe session for use in worker threads.

    This context manager creates a NEW session for the current thread,
    ensuring thread safety when running database operations in QThread
    workers or other background threads.

    Usage in QThread workers:
        ```python
        class MyWorker(QThread):
            def __init__(self, db_path: Path):
                super().__init__()
                self.db_path = db_path

            def run(self):
                with thread_scoped_session(self.db_path) as session:
                    # All database operations use this session
                    repo = MyRepository(session)
                    result = repo.get_all()
                    # Session auto-commits on success, rolls back on exception
        ```

    Args:
        db_path: Path to the project database file.

    Yields:
        Session: A thread-local SQLAlchemy session.

    Note:
        - Each call creates a fresh session - do NOT cache or reuse
        - Session commits automatically on successful context exit
        - Session rolls back automatically on exception
        - Session is always closed when context exits
    """
    if isinstance(db_path, str):
        db_path = Path(db_path)

    factory = project_session_factory(db_path)
    session = factory()
    logger.debug(f"Created thread-scoped session for {db_path}")

    try:
        yield session
        session.commit()
        logger.debug(f"Thread-scoped session committed for {db_path}")
    except Exception as e:
        session.rollback()
        logger.warning(f"Thread-scoped session rolled back for {db_path}: {e}")
        raise
    finally:
        session.close()
        logger.debug(f"Thread-scoped session closed for {db_path}")
