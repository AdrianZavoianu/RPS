"""Database base configuration and session management."""

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from pathlib import Path

# Create data directory if it doesn't exist
DATA_DIR = Path(__file__).parent.parent.parent / "data"
DATA_DIR.mkdir(exist_ok=True)

# Database file path
DB_PATH = DATA_DIR / "rps.db"

# Create engine
engine = create_engine(
    f"sqlite:///{DB_PATH}",
    echo=False,  # Set to True for SQL logging during development
    connect_args={"check_same_thread": False},  # Needed for SQLite
)

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create declarative base
Base = declarative_base()


def get_session():
    """Get a database session."""
    session = SessionLocal()
    try:
        return session
    except Exception:
        session.close()
        raise


def init_db():
    """Initialize database - create all tables."""
    Base.metadata.create_all(bind=engine)
