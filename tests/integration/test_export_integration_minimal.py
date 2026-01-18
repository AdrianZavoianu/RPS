from datetime import datetime
from pathlib import Path

import pandas as pd
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database.base import Base
import database.models as models  # registers models with Base
from services.export_discovery import ExportDiscovery
from services.export_import_data import ImportDataBuilder


class _Context:
    def __init__(self, session_factory):
        self._session_factory = session_factory
        self.slug = "demo"
        self.db_path = Path("demo.db")

    def session(self):
        return self._session_factory()


def _seed_minimal_data(session):
    project = models.Project(name="P1")
    session.add(project)
    session.commit()

    result_set = models.ResultSet(project_id=project.id, name="DES", created_at=datetime.utcnow())
    session.add(result_set)
    session.commit()

    category = models.ResultCategory(
        result_set_id=result_set.id,
        category_name="Envelopes",
        category_type="Global",
    )
    session.add(category)
    session.commit()

    load_case = models.LoadCase(project_id=project.id, name="LC1")
    story = models.Story(project_id=project.id, name="S1", sort_order=1, elevation=0.0)
    session.add_all([load_case, story])
    session.commit()

    drift = models.StoryDrift(
        story_id=story.id,
        load_case_id=load_case.id,
        result_category_id=category.id,
        direction="X",
        drift=0.1,
        story_sort_order=1,
    )
    session.add(drift)
    session.commit()

    # Element cache entry
    element = models.Element(project_id=project.id, element_type="Wall", name="W1", unique_name="W1")
    session.add(element)
    session.commit()

    element_cache = models.ElementResultsCache(
        project_id=project.id,
        result_set_id=result_set.id,
        element_id=element.id,
        story_id=story.id,
        result_type="WallShears_V2",
        story_sort_order=1,
        results_matrix={"LC1": 5.0},
    )
    session.add(element_cache)
    session.commit()

    return project, result_set, category, load_case, story, element


def test_export_discovery_and_import_data_end_to_end(tmp_path):
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)

    # Seed minimal data
    session = SessionLocal()
    project, result_set, category, load_case, story, element = _seed_minimal_data(session)
    project_id = project.id
    result_set_id = result_set.id
    category_id = category.id
    load_case_id = load_case.id
    story_id = story.id
    element_id = element.id
    session.close()

    context = _Context(SessionLocal)

    # Use real discovery to write sheets
    output = tmp_path / "export.xlsx"
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        discovery = ExportDiscovery(context.session, context)
        result_sheets = discovery.discover_and_write(writer, result_set_id, [], None)

        # Build minimal metadata for import data builder
        metadata = {
            "catalog_project": type("CatalogStub", (), {
                "name": "P1",
                "slug": "p1",
                "description": "",
                "created_at": datetime.utcnow(),
            })(),
            "summary": type("SummaryStub", (), {"result_sets": 1, "load_cases": 1, "stories": 1})(),
            "result_sets": [type("RS", (), {"id": result_set_id, "name": "DES", "description": "", "created_at": datetime.utcnow()})()],
            "result_categories": [type("RC", (), {"id": category_id, "result_set_id": result_set_id, "category_name": "Envelopes", "category_type": "Global"})()],
            "load_cases": [type("LC", (), {"name": "LC1", "description": ""})()],
            "stories": [type("ST", (), {"name": "S1", "sort_order": 1, "elevation": 0.0})()],
            "elements": [type("EL", (), {"name": "W1", "unique_name": "W1", "element_type": "Wall"})()],
        }

        ImportDataBuilder(context, app_version="test").write_import_data_sheet(writer, metadata, result_sheets)

    xls = pd.ExcelFile(output)
    sheets = set(xls.sheet_names)
    # Expect global and element sheets plus metadata/import sheets
    assert {"Drifts_X", "WallShears_V2", "IMPORT_DATA"}.issubset(sheets)
