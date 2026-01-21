"""Project database utilities."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Dict
from sqlalchemy import create_engine, Engine
from sqlalchemy.orm import declarative_base, sessionmaker, Session
from sqlalchemy.pool import NullPool

logger = logging.getLogger(__name__)

DATA_DIR = Path(__file__).parent.parent.parent / "data"
DATA_DIR.mkdir(exist_ok=True)
PROJECTS_DIR = DATA_DIR / "projects"
PROJECTS_DIR.mkdir(exist_ok=True)

Base = declarative_base()

# -----------------------------------------------------------------------------
# Engine registry for proper cleanup
# -----------------------------------------------------------------------------

# Track engines per database path for proper disposal
_project_engines: Dict[str, Engine] = {}


def _normalize_db_path(db_path: Path) -> str:
    """Normalize database path for consistent key storage."""
    # Convert to absolute path and use forward slashes
    normalized = str(db_path.resolve()).replace('\\', '/')
    logger.debug(f"Normalized path: {normalized}")
    return normalized


def _get_or_create_engine(db_path: Path) -> Engine:
    """Get or create an engine for the given database path.

    Uses NullPool to avoid connection pooling issues on Windows.
    """
    # Normalize path with forward slashes for consistency
    db_path_str = _normalize_db_path(db_path)

    if db_path_str in _project_engines:
        logger.debug(f"Reusing existing engine for: {db_path_str}")
        return _project_engines[db_path_str]

    db_path.parent.mkdir(parents=True, exist_ok=True)
    logger.debug(f"Creating new engine for: {db_path_str}")
    engine = create_engine(
        f"sqlite:///{db_path}",
        echo=False,
        connect_args={"check_same_thread": False},
        poolclass=NullPool,  # No connection pooling - closes connections immediately
    )
    _project_engines[db_path_str] = engine
    return engine


def dispose_project_engine(db_path: Path | str) -> None:
    """Dispose of the engine for a project database.

    This should be called before deleting a project to ensure all
    database connections are closed.

    Args:
        db_path: Path or string path to the project database
    """
    # Convert to Path if string
    if isinstance(db_path, str):
        db_path = Path(db_path)

    # Normalize path using the same function
    db_path_str = _normalize_db_path(db_path)

    logger.debug(f"Attempting to dispose engine for: {db_path_str}")
    logger.debug(f"Current engines in registry: {list(_project_engines.keys())}")

    if db_path_str in _project_engines:
        engine = _project_engines.pop(db_path_str)
        # Force dispose all connections
        engine.dispose()
        logger.debug(f"Successfully disposed engine for: {db_path_str}")
    else:
        logger.warning(f"Engine not found in registry for disposal: {db_path_str}")
        logger.warning("This might indicate the engine was already disposed or never created")


def dispose_all_engines() -> None:
    """Dispose all project engines (emergency cleanup)."""
    for db_path, engine in list(_project_engines.items()):
        engine.dispose()
        logger.debug(f"Disposed engine: {db_path}")
    _project_engines.clear()


# -----------------------------------------------------------------------------
# Legacy compatibility helpers (used by older tests and utilities)
# -----------------------------------------------------------------------------

# Global in-memory engine for lightweight testing scenarios.
engine = create_engine("sqlite:///:memory:", echo=False)
_SessionLocal = sessionmaker(bind=engine)


def get_session() -> Session:
    """Return a session bound to the global in-memory engine (legacy API)."""
    Base.metadata.create_all(bind=engine)
    return _SessionLocal()


def get_project_db_path(slug: str) -> Path:
    """Get the database path for a project.

    Database is named after the project slug: {slug}.db
    Example: data/projects/160wil/160wil.db
    """
    return PROJECTS_DIR / slug / f"{slug}.db"


def get_project_session(db_path: Path) -> Session:
    engine = _get_or_create_engine(db_path)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    return SessionLocal()


def init_project_db(db_path: Path) -> None:
    engine = _get_or_create_engine(db_path)
    Base.metadata.create_all(bind=engine)


def init_db() -> None:
    """Backward-compatible initializer used by legacy startup code."""
    from database.catalog_base import init_catalog_db

    init_catalog_db()
