
"""Helpers for managing project catalog and per-project databases."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional, List
import shutil

from database.session import (
    get_project_db_path,
    init_project_db,
    get_project_session,
    init_catalog_db,
    get_catalog_session,
    project_session_factory,
)
from database.catalog_repository import CatalogProjectRepository
from database.repository import ProjectRepository, ResultSetRepository
from utils.slug import slugify


def get_session():
    """Return a catalog-level session (legacy helper for CLI/tests)."""
    init_catalog_db()
    return get_catalog_session()


@dataclass
class ProjectContext:
    name: str
    slug: str
    db_path: Path
    description: Optional[str] = None
    created_at: Optional[datetime] = None

    def session(self):
        return project_session_factory(self.db_path)()

    def session_factory(self):
        return project_session_factory(self.db_path)


@dataclass
class ProjectSummary:
    context: ProjectContext
    load_cases: int = 0
    stories: int = 0
    result_sets: int = 0


def _migrate_old_database_if_needed(db_path: Path) -> None:
    """Migrate old project.db to {slug}.db if it exists.

    This provides automatic migration when accessing projects with old naming.
    """
    old_db_path = db_path.parent / "project.db"
    if old_db_path.exists() and not db_path.exists():
        old_db_path.rename(db_path)


def ensure_project_context(name: str, description: Optional[str] = None) -> ProjectContext:
    """Ensure catalog entry and project database exist for the given project name."""
    init_catalog_db()
    catalog_session = get_catalog_session()
    repo = CatalogProjectRepository(catalog_session)

    record = repo.get_by_name(name)
    if record:
        slug = record.slug
        # Always use canonical path based on slug
        db_path = get_project_db_path(slug)

        # Auto-migrate old database naming if needed
        _migrate_old_database_if_needed(db_path)
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
        db_path=db_path,  # Use the canonical path we computed
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

        # Use canonical path based on slug, not what's stored in catalog
        # This handles migration from old project.db to {slug}.db naming
        canonical_db_path = get_project_db_path(record.slug)

        # Auto-migrate old database naming if needed
        _migrate_old_database_if_needed(canonical_db_path)

        return ProjectContext(
            name=record.name,
            slug=record.slug,
            db_path=canonical_db_path,
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
        contexts = []
        for record in records:
            canonical_db_path = get_project_db_path(record.slug)
            # Auto-migrate old database naming if needed
            _migrate_old_database_if_needed(canonical_db_path)

            contexts.append(ProjectContext(
                name=record.name,
                slug=record.slug,
                db_path=canonical_db_path,
                description=record.description,
                created_at=record.created_at,
            ))
        return contexts
    finally:
        session.close()


def get_project_summary(context: ProjectContext) -> ProjectSummary:
    """Return counts for load cases/stories/result sets for a project context."""
    from sqlalchemy.exc import OperationalError

    # Ensure the database is initialized with proper schema
    try:
        init_project_db(context.db_path)
    except Exception:
        # If initialization fails, return empty summary
        return ProjectSummary(context=context)

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
    except OperationalError:
        # If the database has issues (missing tables, corrupted, etc.)
        # Return empty summary rather than crashing
        return ProjectSummary(context=context)
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
    """Delete a project from catalog and remove its database and folder.

    This will:
    1. Remove the project entry from the catalog database
    2. Dispose of the project's database engine to close all connections
    3. Delete the project's database file ({slug}.db)
    4. Remove the entire project folder (data/projects/{slug}/)

    Args:
        name: Project name to delete

    Returns:
        True if project was deleted, False if project not found
    """
    from database.session import dispose_project_engine
    import gc
    import time

    init_catalog_db()
    session = get_catalog_session()
    repo = CatalogProjectRepository(session)
    record = repo.get_by_name(name)
    if not record:
        session.close()
        return False

    # Store db_path before deleting the record
    db_path = Path(record.db_path)
    project_folder = db_path.parent

    # Delete from catalog
    repo.delete(record)
    session.close()

    # Dispose of the project's database engine to close all connections
    # This is critical on Windows where locked files cannot be deleted
    dispose_project_engine(db_path)

    # Force garbage collection to close any lingering connections
    gc.collect()

    # Give a brief moment for file handles to be released
    time.sleep(0.1)

    # Delete the entire project folder (includes database and any other files)
    if project_folder.exists():
        try:
            shutil.rmtree(project_folder)
        except Exception as e:
            # On Windows, files might still be locked. Try again after a brief pause.
            time.sleep(0.2)
            gc.collect()
            try:
                shutil.rmtree(project_folder)
            except Exception as e2:
                # If still failing, raise with details
                raise RuntimeError(
                    f"Failed to delete project folder '{project_folder}': {e2}. "
                    f"The project may still have open database connections."
                )

    return True
