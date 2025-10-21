"""Tests for database models and repositories."""

import pytest
from database.base import get_session
from database.models import Project, LoadCase, Story
from database.repository import ProjectRepository, LoadCaseRepository, StoryRepository


@pytest.fixture
def session():
    """Create a test database session."""
    session = get_session()
    yield session
    session.close()


def test_create_project(session):
    """Test creating a project."""
    repo = ProjectRepository(session)
    project = repo.create(name="Test Project", description="Test description")

    assert project.id is not None
    assert project.name == "Test Project"
    assert project.description == "Test description"

    # Cleanup
    repo.delete(project.id)


def test_get_project_by_name(session):
    """Test retrieving project by name."""
    repo = ProjectRepository(session)

    # Create project
    project = repo.create(name="Test Project 2")

    # Retrieve it
    retrieved = repo.get_by_name("Test Project 2")

    assert retrieved is not None
    assert retrieved.id == project.id
    assert retrieved.name == "Test Project 2"

    # Cleanup
    repo.delete(project.id)


def test_create_load_case(session):
    """Test creating a load case."""
    # Create project first
    project_repo = ProjectRepository(session)
    project = project_repo.create(name="Test Project 3")

    # Create load case
    case_repo = LoadCaseRepository(session)
    load_case = case_repo.create(
        project_id=project.id,
        name="TH01",
        case_type="Time History"
    )

    assert load_case.id is not None
    assert load_case.name == "TH01"
    assert load_case.case_type == "Time History"
    assert load_case.project_id == project.id

    # Cleanup
    project_repo.delete(project.id)


def test_create_story(session):
    """Test creating a story."""
    # Create project first
    project_repo = ProjectRepository(session)
    project = project_repo.create(name="Test Project 4")

    # Create story
    story_repo = StoryRepository(session)
    story = story_repo.create(
        project_id=project.id,
        name="Floor 1",
        elevation=3.5,
        sort_order=1
    )

    assert story.id is not None
    assert story.name == "Floor 1"
    assert story.elevation == 3.5
    assert story.sort_order == 1

    # Cleanup
    project_repo.delete(project.id)


def test_get_or_create(session):
    """Test get_or_create functionality."""
    project_repo = ProjectRepository(session)
    project = project_repo.create(name="Test Project 5")

    case_repo = LoadCaseRepository(session)

    # Create new case
    case1 = case_repo.get_or_create(project.id, "TH01")
    assert case1.id is not None

    # Get existing case
    case2 = case_repo.get_or_create(project.id, "TH01")
    assert case1.id == case2.id  # Should be same object

    # Cleanup
    project_repo.delete(project.id)
