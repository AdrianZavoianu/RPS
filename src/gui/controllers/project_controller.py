"""Controller utilities for project-related GUI actions."""

from __future__ import annotations

from typing import Optional

from services.project_service import (
    ProjectContext,
    delete_project_context,
    ensure_project_context,
    get_project_context,
    list_project_summaries,
)
from services.project_runtime import ProjectRuntime, build_project_runtime


class ProjectController:
    """High-level orchestration for project CRUD used by the UI."""

    def list_summaries(self):
        return list_project_summaries()

    def ensure_context(self, name: str, description: Optional[str] = None) -> ProjectContext:
        return ensure_project_context(name, description)

    def get_context(self, name: str) -> Optional[ProjectContext]:
        return get_project_context(name)

    def delete_project(self, name: str) -> bool:
        return delete_project_context(name)

    def build_runtime(self, context: ProjectContext) -> ProjectRuntime:
        return build_project_runtime(context)
