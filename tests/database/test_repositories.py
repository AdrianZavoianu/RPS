"""Tests for repository classes - database operations and queries."""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from database.models import Base, Project, Story, ResultSet, GlobalResultsCache
from database.repositories.project import ProjectRepository
from database.repositories.cache import CacheRepository
from database.base_repository import BaseRepository


@pytest.fixture
def test_engine():
    """Create an in-memory SQLite engine for testing."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return engine


@pytest.fixture
def test_session(test_engine):
    """Create a session for testing."""
    SessionLocal = sessionmaker(bind=test_engine)
    session = SessionLocal()
    yield session
    session.close()


class TestBaseRepository:
    """Tests for BaseRepository base class."""

    def test_create_and_commit(self, test_session):
        """Test that create() adds and commits to database."""
        repo = ProjectRepository(test_session)

        project = repo.create(name="Test Project")

        assert project.id is not None
        assert project.name == "Test Project"

    def test_get_by_id(self, test_session):
        """Test get_by_id retrieves correct entity."""
        repo = ProjectRepository(test_session)
        project = repo.create(name="Test Project")

        retrieved = repo.get_by_id(project.id)

        assert retrieved is not None
        assert retrieved.id == project.id
        assert retrieved.name == "Test Project"

    def test_get_by_id_returns_none_for_missing(self, test_session):
        """Test get_by_id returns None for non-existent ID."""
        repo = ProjectRepository(test_session)

        retrieved = repo.get_by_id(9999)

        assert retrieved is None

    def test_delete_removes_entity(self, test_session):
        """Test delete() removes entity from database."""
        repo = ProjectRepository(test_session)
        project = repo.create(name="To Delete")
        project_id = project.id

        # ProjectRepository.delete() takes id, not entity
        result = repo.delete(project_id)

        assert result is True
        assert repo.get_by_id(project_id) is None

    def test_list_all_returns_all_entities(self, test_session):
        """Test list_all returns all entities."""
        repo = ProjectRepository(test_session)
        repo.create(name="Project 1")
        repo.create(name="Project 2")
        repo.create(name="Project 3")

        all_projects = repo.list_all()

        assert len(all_projects) == 3


class TestProjectRepository:
    """Tests for ProjectRepository specific methods."""

    def test_get_by_name(self, test_session):
        """Test get_by_name finds project."""
        repo = ProjectRepository(test_session)
        repo.create(name="Unique Name")

        result = repo.get_by_name("Unique Name")

        assert result is not None
        assert result.name == "Unique Name"

    def test_get_by_name_returns_none_for_missing(self, test_session):
        """Test get_by_name returns None for missing name."""
        repo = ProjectRepository(test_session)

        result = repo.get_by_name("Non-Existent")

        assert result is None

    def test_get_all_returns_all_projects(self, test_session):
        """Test get_all returns all projects."""
        repo = ProjectRepository(test_session)
        repo.create(name="First")
        repo.create(name="Second")
        repo.create(name="Third")

        all_projects = repo.get_all()

        # Should return all 3 projects
        assert len(all_projects) == 3
        names = {p.name for p in all_projects}
        assert names == {"First", "Second", "Third"}

    def test_delete_returns_true_on_success(self, test_session):
        """Test delete returns True when successful."""
        repo = ProjectRepository(test_session)
        project = repo.create(name="To Delete")

        result = repo.delete(project.id)

        assert result is True

    def test_delete_returns_false_for_missing(self, test_session):
        """Test delete returns False when project not found."""
        repo = ProjectRepository(test_session)

        result = repo.delete(9999)

        assert result is False


class TestCacheRepository:
    """Tests for CacheRepository (GlobalResultsCache)."""

    @pytest.fixture
    def setup_project_and_story(self, test_session):
        """Create a project and story for cache tests."""
        # Create project
        project = Project(name="Test Project")
        test_session.add(project)
        test_session.commit()

        # Create result set
        result_set = ResultSet(project_id=project.id, name="DES")
        test_session.add(result_set)
        test_session.commit()

        # Create story
        story = Story(project_id=project.id, name="L1", sort_order=1)
        test_session.add(story)
        test_session.commit()

        return {
            "project_id": project.id,
            "result_set_id": result_set.id,
            "story_id": story.id,
        }

    def test_upsert_creates_new_entry(self, test_session, setup_project_and_story):
        """Test upsert_cache_entry creates new entry."""
        repo = CacheRepository(test_session)
        data = setup_project_and_story

        cache = repo.upsert_cache_entry(
            project_id=data["project_id"],
            story_id=data["story_id"],
            result_type="Drifts_X",
            results_matrix={"TH01": 0.1, "TH02": 0.15},
            result_set_id=data["result_set_id"],
        )

        assert cache.id is not None
        assert cache.result_type == "Drifts_X"
        assert cache.results_matrix == {"TH01": 0.1, "TH02": 0.15}

    def test_upsert_updates_existing_entry(self, test_session, setup_project_and_story):
        """Test upsert_cache_entry updates existing entry."""
        repo = CacheRepository(test_session)
        data = setup_project_and_story

        # Create initial entry
        cache1 = repo.upsert_cache_entry(
            project_id=data["project_id"],
            story_id=data["story_id"],
            result_type="Drifts_X",
            results_matrix={"TH01": 0.1},
            result_set_id=data["result_set_id"],
        )

        # Upsert with new values
        cache2 = repo.upsert_cache_entry(
            project_id=data["project_id"],
            story_id=data["story_id"],
            result_type="Drifts_X",
            results_matrix={"TH01": 0.2, "TH02": 0.25},
            result_set_id=data["result_set_id"],
        )

        # Should be same record with updated values
        assert cache1.id == cache2.id
        assert cache2.results_matrix == {"TH01": 0.2, "TH02": 0.25}

    def test_get_distinct_load_cases(self, test_session, setup_project_and_story):
        """Test get_distinct_load_cases extracts keys from results_matrix."""
        repo = CacheRepository(test_session)
        data = setup_project_and_story

        repo.upsert_cache_entry(
            project_id=data["project_id"],
            story_id=data["story_id"],
            result_type="Drifts_X",
            results_matrix={"TH01": 0.1, "TH02": 0.15, "TH03": 0.2},
            result_set_id=data["result_set_id"],
        )

        load_cases = repo.get_distinct_load_cases(
            data["project_id"], data["result_set_id"]
        )

        assert set(load_cases) == {"TH01", "TH02", "TH03"}

    def test_get_distinct_load_cases_returns_empty_for_missing(self, test_session):
        """Test get_distinct_load_cases returns empty list for missing data."""
        repo = CacheRepository(test_session)

        load_cases = repo.get_distinct_load_cases(9999, 9999)

        assert load_cases == []

    def test_clear_cache_for_project(self, test_session, setup_project_and_story):
        """Test clear_cache_for_project removes all entries."""
        repo = CacheRepository(test_session)
        data = setup_project_and_story

        # Create some cache entries
        repo.upsert_cache_entry(
            project_id=data["project_id"],
            story_id=data["story_id"],
            result_type="Drifts_X",
            results_matrix={"TH01": 0.1},
            result_set_id=data["result_set_id"],
        )
        repo.upsert_cache_entry(
            project_id=data["project_id"],
            story_id=data["story_id"],
            result_type="Drifts_Y",
            results_matrix={"TH01": 0.05},
            result_set_id=data["result_set_id"],
        )

        # Clear all cache for project
        repo.clear_cache_for_project(data["project_id"])

        # Verify cleared
        load_cases = repo.get_distinct_load_cases(
            data["project_id"], data["result_set_id"]
        )
        assert load_cases == []

    def test_clear_cache_for_project_with_filter(
        self, test_session, setup_project_and_story
    ):
        """Test clear_cache_for_project with result_type filter."""
        repo = CacheRepository(test_session)
        data = setup_project_and_story

        # Create cache entries for different result types
        repo.upsert_cache_entry(
            project_id=data["project_id"],
            story_id=data["story_id"],
            result_type="Drifts_X",
            results_matrix={"TH01": 0.1},
            result_set_id=data["result_set_id"],
        )
        repo.upsert_cache_entry(
            project_id=data["project_id"],
            story_id=data["story_id"],
            result_type="Forces_X",
            results_matrix={"TH01": 100},
            result_set_id=data["result_set_id"],
        )

        # Clear only Drifts_X
        repo.clear_cache_for_project(data["project_id"], result_type="Drifts_X")

        # Verify Drifts_X cleared but Forces_X remains
        entries = repo.get_cache_for_display(
            data["project_id"], "Forces_X", data["result_set_id"]
        )
        assert len(entries) == 1

        drifts = repo.get_cache_for_display(
            data["project_id"], "Drifts_X", data["result_set_id"]
        )
        assert len(drifts) == 0


class TestRepositoryImports:
    """Tests for repository module imports and re-exports."""

    def test_main_repository_module_exports(self):
        """Test that main repository module re-exports all repositories."""
        from database.repository import (
            ProjectRepository,
            LoadCaseRepository,
            StoryRepository,
            ResultSetRepository,
            ElementRepository,
            CacheRepository,
            PushoverCaseRepository,
        )

        # Just verify imports work
        assert ProjectRepository is not None
        assert LoadCaseRepository is not None
        assert StoryRepository is not None
        assert ResultSetRepository is not None
        assert ElementRepository is not None
        assert CacheRepository is not None
        assert PushoverCaseRepository is not None

    def test_repositories_package_imports(self):
        """Test that repositories package exports all repositories."""
        from database.repositories import (
            ProjectRepository,
            CacheRepository,
            ElementCacheRepository,
            JointCacheRepository,
            AbsoluteMaxMinDriftRepository,
            ResultCategoryRepository,
        )

        # Just verify imports work
        assert ProjectRepository is not None
        assert CacheRepository is not None
        assert ElementCacheRepository is not None
        assert JointCacheRepository is not None
        assert AbsoluteMaxMinDriftRepository is not None
        assert ResultCategoryRepository is not None
