from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database.base import Base
import database.models as models  # registers models with Base
from processing.metadata_importer import MetadataImporter


def test_metadata_importer_creates_project_and_result_set_and_category():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()

    importer = MetadataImporter(
        session=session,
        project_name="P1",
        result_set_name="DES",
    )

    stats, project_id, category_id = importer.ensure_project_and_result_set()

    assert stats["project"] == "P1"
    assert stats["result_set_id"] is not None
    assert project_id == stats["project_id"]
    assert category_id is not None

    # Ensure DB objects were created
    assert session.query(models.Project).count() == 1
    assert session.query(models.ResultSet).count() == 1
    assert session.query(models.ResultCategory).count() == 1

    # Idempotent call should not duplicate
    stats2, project_id2, category_id2 = importer.ensure_project_and_result_set()
    assert stats2["project_id"] == project_id
    assert project_id2 == project_id
    assert category_id2 == category_id
    assert session.query(models.Project).count() == 1
    assert session.query(models.ResultSet).count() == 1

    session.close()
