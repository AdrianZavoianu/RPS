"""Runtime helpers that assemble per-project repositories and services."""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.orm import Session

from database.repository import (
    AbsoluteMaxMinDriftRepository,
    CacheRepository,
    ElementCacheRepository,
    ElementRepository,
    JointCacheRepository,
    LoadCaseRepository,
    ProjectRepository,
    ResultSetRepository,
    StoryRepository,
)
from processing.result_service import ResultDataService
from services.project_service import ProjectContext


@dataclass
class ProjectRepositories:
    project: ProjectRepository
    result_set: ResultSetRepository
    cache: CacheRepository
    story: StoryRepository
    load_case: LoadCaseRepository
    abs_maxmin: AbsoluteMaxMinDriftRepository
    element: ElementRepository
    element_cache: ElementCacheRepository
    joint_cache: JointCacheRepository


@dataclass
class ProjectRuntime:
    context: ProjectContext
    session: Session
    project: object
    repos: ProjectRepositories
    result_service: ResultDataService

    def dispose(self) -> None:
        """Dispose of the underlying SQLAlchemy session."""
        if self.session:
            self.session.close()
            self.session = None


def build_project_runtime(context: ProjectContext) -> ProjectRuntime:
    """Create repositories and a result service for a project context."""

    session = context.session()
    repos = ProjectRepositories(
        project=ProjectRepository(session),
        result_set=ResultSetRepository(session),
        cache=CacheRepository(session),
        story=StoryRepository(session),
        load_case=LoadCaseRepository(session),
        abs_maxmin=AbsoluteMaxMinDriftRepository(session),
        element=ElementRepository(session),
        element_cache=ElementCacheRepository(session),
        joint_cache=JointCacheRepository(session),
    )

    project = repos.project.get_by_name(context.name)
    if not project:
        session.close()
        raise ValueError(f"Project '{context.name}' is not initialized in its database.")

    result_service = ResultDataService(
        project_id=project.id,
        cache_repo=repos.cache,
        story_repo=repos.story,
        load_case_repo=repos.load_case,
        abs_maxmin_repo=repos.abs_maxmin,
        element_cache_repo=repos.element_cache,
        element_repo=repos.element,
        joint_cache_repo=repos.joint_cache,
        session=session,
    )

    return ProjectRuntime(
        context=context,
        session=session,
        project=project,
        repos=repos,
        result_service=result_service,
    )
