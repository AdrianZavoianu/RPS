"""Project database utilities."""

from __future__ import annotations

from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker, Session


DATA_DIR = Path(__file__).parent.parent.parent / "data"
DATA_DIR.mkdir(exist_ok=True)
PROJECTS_DIR = DATA_DIR / "projects"
PROJECTS_DIR.mkdir(exist_ok=True)

Base = declarative_base()

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


def _create_engine(db_path: Path):
    db_path.parent.mkdir(parents=True, exist_ok=True)
    return create_engine(
        f"sqlite:///{db_path}",
        echo=False,
        connect_args={"check_same_thread": False},
    )


def get_project_session(db_path: Path) -> Session:
    engine = _create_engine(db_path)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    return SessionLocal()


def init_project_db(db_path: Path) -> None:
    engine = _create_engine(db_path)
    Base.metadata.create_all(bind=engine)


def init_db() -> None:
    """Backward-compatible initializer used by legacy startup code."""
    from database.catalog_base import init_catalog_db

    init_catalog_db()
