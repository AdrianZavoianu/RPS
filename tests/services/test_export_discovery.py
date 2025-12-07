"""Tests for export discovery service."""

import pytest

from database.base import Base, engine, get_session
from database.models import (
    ElementResultsCache,
    GlobalResultsCache,
    JointResultsCache,
    PushoverCase,
)
from database.repository import (
    ElementRepository,
    ProjectRepository,
    ResultSetRepository,
    StoryRepository,
)
from services.export_discovery import ExportDiscoveryService


@pytest.fixture()
def session_factory():
    Base.metadata.create_all(bind=engine)

    def factory():
        return get_session()

    yield factory
    Base.metadata.drop_all(bind=engine)


def test_discover_result_sets_filters_by_context(session_factory):
    session = session_factory()
    project_repo = ProjectRepository(session)
    result_set_repo = ResultSetRepository(session)

    project = project_repo.create("TestProject")
    project_name = project.name
    result_set_repo.create(project_id=project.id, name="DES")
    pushover_set = result_set_repo.create(project_id=project.id, name="PUSH")
    pushover_set.analysis_type = "Pushover"
    session.commit()
    session.close()

    service = ExportDiscoveryService(session_factory)

    nltha_sets = service.discover_result_sets(project_name, "NLTHA")
    pushover_sets = service.discover_result_sets(project_name, "Pushover")

    assert [rs.name for rs in nltha_sets] == ["DES"]
    assert [rs.name for rs in pushover_sets] == ["PUSH"]


def test_discover_result_types_extracts_base_types_and_curves(session_factory):
    session = session_factory()
    project_repo = ProjectRepository(session)
    result_set_repo = ResultSetRepository(session)
    story_repo = StoryRepository(session)
    element_repo = ElementRepository(session)

    project = project_repo.create("TypesProject")
    result_set = result_set_repo.create(project_id=project.id, name="PUSH")
    result_set.analysis_type = "Pushover"
    result_set_id = result_set.id

    story = story_repo.create(project_id=project.id, name="L1", sort_order=0)
    element = element_repo.create(
        project_id=project.id,
        element_type="Wall",
        name="P1",
        unique_name="P1",
        story_id=story.id,
    )

    session.add(
        GlobalResultsCache(
            project_id=project.id,
            result_set_id=result_set_id,
            result_type="Drifts",
            story_id=story.id,
            results_matrix={"LC1": 0.1},
        )
    )
    session.add(
        ElementResultsCache(
            project_id=project.id,
            result_set_id=result_set_id,
            result_type="WallShears_V2",
            element_id=element.id,
            story_id=story.id,
            results_matrix={"LC1": 1.0},
        )
    )
    session.add(
        ElementResultsCache(
            project_id=project.id,
            result_set_id=result_set_id,
            result_type="BeamRotations",
            element_id=element.id,
            story_id=story.id,
            results_matrix={"LC1": 2.0},
        )
    )
    session.add(
        JointResultsCache(
            project_id=project.id,
            result_set_id=result_set_id,
            result_type="SoilPressures_Min",
            shell_object="F1",
            unique_name="F1",
            results_matrix={"LC1": -10.0},
        )
    )
    session.add(
        JointResultsCache(
            project_id=project.id,
            result_set_id=result_set_id,
            result_type="JointDisplacements_Ux",
            shell_object="J1",
            unique_name="J1",
            results_matrix={"LC1": 0.5},
        )
    )
    session.add(
        PushoverCase(
            project_id=project.id,
            result_set_id=result_set_id,
            name="Push_Mod_X+Ecc+",
            direction="X",
            base_story="Base",
        )
    )
    session.commit()
    session.close()

    service = ExportDiscoveryService(session_factory)
    types = service.discover_result_types([result_set_id], "Pushover")

    assert "Curves" in types.global_types
    assert "Drifts" in types.global_types
    assert set(types.element_types) == {"BeamRotations", "WallShears"}
    assert set(types.joint_types) == {"JointDisplacements", "SoilPressures"}
