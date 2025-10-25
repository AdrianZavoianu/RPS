from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker, Session

DATA_DIR = Path(__file__).parent.parent.parent / "data"
DATA_DIR.mkdir(exist_ok=True)

CATALOG_DB_PATH = DATA_DIR / "catalog.db"

CatalogBase = declarative_base()

_catalog_engine = create_engine(
    f"sqlite:///{CATALOG_DB_PATH}",
    echo=False,
    connect_args={"check_same_thread": False},
)
CatalogSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=_catalog_engine)


def get_catalog_session() -> Session:
    return CatalogSessionLocal()


def init_catalog_db() -> None:
    CatalogBase.metadata.create_all(bind=_catalog_engine)
