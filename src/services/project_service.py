
"""Helpers for managing project catalog and per-project databases."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional, List
import shutil

from database.base import get_project_db_path, init_project_db, get_project_session
from database.catalog_base import init_catalog_db, get_catalog_session
from database.catalog_repository import CatalogProjectRepository
from database.repository import ProjectRepository, ResultSetRepository
from utils.slug import slugify


@dataclass
class ProjectContext:
    name: str
    slug: str
    db_path: Path
    description: Optional[str] = None
    created_at: Optional[datetime] = None

    def session(self):
        return get_project_session(self.db_path)

    def session_factory(self):
        def factory():
            return get_project_session(self.db_path)
        return factory


@dataclass
class ProjectSummary:
    context: ProjectContext
    load_cases: int = 0
    stories: int = 0
    result_sets: int = 0


def ensure_project_context(name: str, description: Optional[str] = None) -> ProjectContext:
    """Ensure catalog entry and project database exist for the given project name."""
    init_catalog_db()
    catalog_session = get_catalog_session()
    repo = CatalogProjectRepository(catalog_session)

    record = repo.get_by_name(name)
    if record:
        slug = record.slug
        db_path = Path(record.db_path)
    else:
        base_slug = slugify(name)
        slug = base_slug
        counter = 1
        while repo.get_by_slug(slug):
            slug = f"{base_slug}-{counter}"
            counter += 1
        db_path = get_project_db_path(slug)
        record = repo.create(name=name, slug=slug, db_path=db_path, description=description)

    catalog_session.close()

    init_project_db(db_path)

    session = get_project_session(db_path)
    try:
        project_repo = ProjectRepository(session)
        if not project_repo.get_by_name(name):
            project_repo.create(name=name, description=description)
    finally:
        session.close()

    return ProjectContext(
        name=record.name,
        slug=record.slug,
        db_path=Path(record.db_path),
        description=record.description,
        created_at=record.created_at,
    )


def get_project_context(name: str) -> Optional[ProjectContext]:
    init_catalog_db()
    session = get_catalog_session()
    try:
        record = CatalogProjectRepository(session).get_by_name(name)
        if not record:
            return None
        return ProjectContext(
            name=record.name,
            slug=record.slug,
            db_path=Path(record.db_path),
            description=record.description,
            created_at=record.created_at,
        )
    finally:
        session.close()


def list_project_contexts() -> List[ProjectContext]:
    init_catalog_db()
    session = get_catalog_session()
    try:
        records = CatalogProjectRepository(session).get_all()
        return [
            ProjectContext(
                name=record.name,
                slug=record.slug,
                db_path=Path(record.db_path),
                description=record.description,
                created_at=record.created_at,
            )
            for record in records
        ]
    finally:
        session.close()


def get_project_summary(context: ProjectContext) -> ProjectSummary:
    """Return counts for load cases/stories/result sets for a project context."""
    session = context.session()
    try:
        project_repo = ProjectRepository(session)
        project = project_repo.get_by_name(context.name)
        if not project:
            return ProjectSummary(context=context)

        load_case_count = len(project.load_cases)
        story_count = len(project.stories)
        result_set_count = len(project.result_sets)

        return ProjectSummary(
            context=context,
            load_cases=load_case_count,
            stories=story_count,
            result_sets=result_set_count,
        )
    finally:
        session.close()


def list_project_summaries() -> List[ProjectSummary]:
    """Return summaries for all known projects."""
    summaries: List[ProjectSummary] = []
    for context in list_project_contexts():
        summaries.append(get_project_summary(context))
    return summaries


def result_set_exists(context: ProjectContext, result_set_name: str) -> bool:
    session = context.session()
    try:
        project_repo = ProjectRepository(session)
        project = project_repo.get_by_name(context.name)
        if not project:
            return False
        result_repo = ResultSetRepository(session)
        return result_repo.check_duplicate(project.id, result_set_name)
    finally:
        session.close()


def delete_project_context(name: str) -> bool:
    init_catalog_db()
    session = get_catalog_session()
    repo = CatalogProjectRepository(session)
    record = repo.get_by_name(name)
    if not record:
        session.close()
        return False
    repo.delete(record)
    session.close()

    db_path = Path(record.db_path)
    if db_path.exists():
        shutil.rmtree(db_path.parent, ignore_errors=True)
    return True
