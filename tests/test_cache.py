"""Test cache repository and wide-format data model."""

import pytest
from database.base import Base, engine, get_session
from database.repository import (
    ProjectRepository,
    StoryRepository,
    LoadCaseRepository,
    ResultRepository,
    ResultSetRepository,
    CacheRepository,
)
from database.models import StoryDrift


@pytest.fixture(scope="function")
def test_session():
    """Create a test database session."""
    Base.metadata.create_all(bind=engine)
    session = get_session()
    yield session
    session.close()
    Base.metadata.drop_all(bind=engine)


def test_create_result_set(test_session):
    """Test creating a result set."""
    project_repo = ProjectRepository(test_session)
    result_set_repo = ResultSetRepository(test_session)

    project = project_repo.create("TestProject")
    result_set = result_set_repo.create(
        project_id=project.id,
        name="DES",
        result_category="Envelopes",
        description="Design envelope results",
    )

    assert result_set.id is not None
    assert result_set.name == "DES"
    assert result_set.result_category == "Envelopes"
    assert result_set.project_id == project.id


def test_cache_upsert(test_session):
    """Test upserting cache entries."""
    project_repo = ProjectRepository(test_session)
    story_repo = StoryRepository(test_session)
    cache_repo = CacheRepository(test_session)

    project = project_repo.create("TestProject")
    story = story_repo.create(project_id=project.id, name="Story1", sort_order=1)

    # Create cache entry
    results_matrix = {"TH01_X": 0.0023, "TH01_Y": 0.0019, "MCR1_X": 0.0021}
    cache_entry = cache_repo.upsert_cache_entry(
        project_id=project.id,
        story_id=story.id,
        result_type="Drifts",
        results_matrix=results_matrix,
    )

    assert cache_entry.id is not None
    assert cache_entry.results_matrix == results_matrix
    assert cache_entry.result_type == "Drifts"

    # Update same entry
    updated_matrix = {"TH01_X": 0.0025, "TH01_Y": 0.0020, "MCR1_X": 0.0022, "MCR2_X": 0.0018}
    updated_entry = cache_repo.upsert_cache_entry(
        project_id=project.id,
        story_id=story.id,
        result_type="Drifts",
        results_matrix=updated_matrix,
    )

    # Should be same entry (updated)
    assert updated_entry.id == cache_entry.id
    assert updated_entry.results_matrix == updated_matrix
    assert len(updated_entry.results_matrix) == 4


def test_get_cache_for_display(test_session):
    """Test retrieving cache data for display."""
    project_repo = ProjectRepository(test_session)
    story_repo = StoryRepository(test_session)
    cache_repo = CacheRepository(test_session)

    project = project_repo.create("TestProject")

    # Create multiple stories
    story1 = story_repo.create(project_id=project.id, name="Story1", sort_order=1)
    story2 = story_repo.create(project_id=project.id, name="Story2", sort_order=2)
    story3 = story_repo.create(project_id=project.id, name="Story3", sort_order=3)

    # Create cache entries
    cache_repo.upsert_cache_entry(
        project_id=project.id,
        story_id=story1.id,
        result_type="Drifts",
        results_matrix={"TH01_X": 0.0023, "TH01_Y": 0.0019},
    )
    cache_repo.upsert_cache_entry(
        project_id=project.id,
        story_id=story2.id,
        result_type="Drifts",
        results_matrix={"TH01_X": 0.0031, "TH01_Y": 0.0028},
    )
    cache_repo.upsert_cache_entry(
        project_id=project.id,
        story_id=story3.id,
        result_type="Drifts",
        results_matrix={"TH01_X": 0.0045, "TH01_Y": 0.0041},
    )

    # Retrieve for display (should be ordered by sort_order descending)
    cache_entries = cache_repo.get_cache_for_display(
        project_id=project.id,
        result_type="Drifts",
    )

    assert len(cache_entries) == 3
    # Check order (descending by sort_order)
    assert cache_entries[0].story_id == story3.id
    assert cache_entries[1].story_id == story2.id
    assert cache_entries[2].story_id == story1.id


def test_cache_integration_with_normalized_data(test_session):
    """Test that cache can be generated from normalized drift data."""
    project_repo = ProjectRepository(test_session)
    story_repo = StoryRepository(test_session)
    load_case_repo = LoadCaseRepository(test_session)
    result_repo = ResultRepository(test_session)
    cache_repo = CacheRepository(test_session)

    # Create test data
    project = project_repo.create("TestProject")
    story1 = story_repo.create(project_id=project.id, name="Story1", sort_order=1)
    story2 = story_repo.create(project_id=project.id, name="Story2", sort_order=2)

    lc1 = load_case_repo.create(project_id=project.id, name="TH01")
    lc2 = load_case_repo.create(project_id=project.id, name="MCR1")

    # Create normalized drift records
    drifts = [
        StoryDrift(story_id=story1.id, load_case_id=lc1.id, direction="X", drift=0.0023),
        StoryDrift(story_id=story1.id, load_case_id=lc1.id, direction="Y", drift=0.0019),
        StoryDrift(story_id=story1.id, load_case_id=lc2.id, direction="X", drift=0.0021),
        StoryDrift(story_id=story2.id, load_case_id=lc1.id, direction="X", drift=0.0031),
        StoryDrift(story_id=story2.id, load_case_id=lc1.id, direction="Y", drift=0.0028),
        StoryDrift(story_id=story2.id, load_case_id=lc2.id, direction="X", drift=0.0029),
    ]
    result_repo.bulk_create_drifts(drifts)

    # Generate cache from normalized data
    from database.models import LoadCase, Story

    all_drifts = (
        test_session.query(StoryDrift, LoadCase.name)
        .join(LoadCase, StoryDrift.load_case_id == LoadCase.id)
        .join(Story, StoryDrift.story_id == Story.id)
        .filter(Story.project_id == project.id)
        .all()
    )

    story_matrices = {}
    for drift, load_case_name in all_drifts:
        story_id = drift.story_id
        if story_id not in story_matrices:
            story_matrices[story_id] = {}

        key = f"{load_case_name}_{drift.direction}"
        story_matrices[story_id][key] = drift.drift

    # Upsert cache
    for story_id, results_matrix in story_matrices.items():
        cache_repo.upsert_cache_entry(
            project_id=project.id,
            story_id=story_id,
            result_type="Drifts",
            results_matrix=results_matrix,
        )

    # Verify cache
    cache_entries = cache_repo.get_cache_for_display(project_id=project.id, result_type="Drifts")
    assert len(cache_entries) == 2

    # Verify story1 cache
    story1_cache = next(c for c in cache_entries if c.story_id == story1.id)
    assert "TH01_X" in story1_cache.results_matrix
    assert "TH01_Y" in story1_cache.results_matrix
    assert "MCR1_X" in story1_cache.results_matrix
    assert story1_cache.results_matrix["TH01_X"] == 0.0023

    # Verify story2 cache
    story2_cache = next(c for c in cache_entries if c.story_id == story2.id)
    assert "TH01_X" in story2_cache.results_matrix
    assert "TH01_Y" in story2_cache.results_matrix
    assert "MCR1_X" in story2_cache.results_matrix
    assert story2_cache.results_matrix["TH01_X"] == 0.0031
