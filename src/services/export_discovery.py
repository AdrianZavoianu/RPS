"""Discovery helpers for export dialogs and services.

Centralizes logic for finding result sets and available result types
based on the current analysis context (NLTHA vs Pushover) so UI layers
don't duplicate database queries.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Iterable, List

from sqlalchemy.orm import Session

from config.analysis_types import AnalysisType, normalize_analysis_type
from database.models import (
    ElementResultsCache,
    GlobalResultsCache,
    JointResultsCache,
    PushoverCase,
)
from database.repository import ProjectRepository, ResultSetRepository

# Alias for a factory that returns a new SQLAlchemy session.
SessionFactory = Callable[[], Session]


@dataclass
class ResultSetSummary:
    """Lightweight view of a result set for export selection."""

    id: int
    name: str
    analysis_type: str | None = None


@dataclass
class ExportTypeBuckets:
    """Grouped lists of available result types."""

    global_types: List[str] = field(default_factory=list)
    element_types: List[str] = field(default_factory=list)
    joint_types: List[str] = field(default_factory=list)


@dataclass
class ExportDiscoveryResult:
    """Container for export discovery output."""

    result_sets: List[ResultSetSummary]
    types: ExportTypeBuckets


class ExportDiscoveryService:
    """Service for export-related discovery queries."""

    def __init__(self, session_factory: SessionFactory):
        self._session_factory = session_factory

    def discover(self, project_name: str, analysis_context: str | None) -> ExportDiscoveryResult:
        """Discover both result sets and types for the given context."""
        result_sets = self.discover_result_sets(project_name, analysis_context)
        result_set_ids = [rs.id for rs in result_sets]
        types = self.discover_result_types(result_set_ids, analysis_context)
        return ExportDiscoveryResult(result_sets=result_sets, types=types)

    def discover_result_sets(self, project_name: str, analysis_context: str | None) -> List[ResultSetSummary]:
        """Return result sets filtered by analysis context."""
        normalized_context = normalize_analysis_type(analysis_context)
        with self._session_factory() as session:
            project_repo = ProjectRepository(session)
            project = project_repo.get_by_name(project_name)
            if not project:
                return []

            result_set_repo = ResultSetRepository(session)
            all_sets = result_set_repo.get_by_project(project.id)

            if normalized_context == AnalysisType.PUSHOVER:
                filtered_sets = [rs for rs in all_sets if getattr(rs, "analysis_type", None) == "Pushover"]
            else:
                filtered_sets = [rs for rs in all_sets if getattr(rs, "analysis_type", None) != "Pushover"]

            return [
                ResultSetSummary(
                    id=rs.id,
                    name=rs.name,
                    analysis_type=getattr(rs, "analysis_type", None),
                )
                for rs in filtered_sets
            ]

    def discover_result_types(self, result_set_ids: Iterable[int], analysis_context: str | None) -> ExportTypeBuckets:
        """Return available result types grouped by category for the given result sets."""
        ids = list(result_set_ids)
        buckets = ExportTypeBuckets()
        if not ids:
            return buckets

        normalized_context = normalize_analysis_type(analysis_context)

        with self._session_factory() as session:
            if normalized_context == AnalysisType.PUSHOVER:
                has_curves = (
                    session.query(PushoverCase.id)
                    .filter(PushoverCase.result_set_id.in_(ids))
                    .first()
                )
                if has_curves:
                    buckets.global_types.append("Curves")

            global_rows = (
                session.query(GlobalResultsCache.result_type)
                .filter(GlobalResultsCache.result_set_id.in_(ids))
                .distinct()
                .all()
            )
            buckets.global_types.extend(sorted(row[0] for row in global_rows))

            element_rows = (
                session.query(ElementResultsCache.result_type)
                .filter(ElementResultsCache.result_set_id.in_(ids))
                .distinct()
                .all()
            )
            element_base_types = {self._extract_element_base_type(row[0]) for row in element_rows}
            buckets.element_types = sorted(element_base_types)

            joint_rows = (
                session.query(JointResultsCache.result_type)
                .filter(JointResultsCache.result_set_id.in_(ids))
                .distinct()
                .all()
            )
            joint_base_types = {self._extract_joint_base_type(row[0]) for row in joint_rows}
            buckets.joint_types = sorted(joint_base_types)

        return buckets

    @staticmethod
    def _extract_element_base_type(result_type: str) -> str:
        """Strip element direction suffixes (_V2/_V3/_R2/_R3) to base type."""
        if any(suffix in result_type for suffix in ("_V2", "_V3", "_R2", "_R3")):
            return result_type.rsplit("_", 1)[0]
        return result_type

    @staticmethod
    def _extract_joint_base_type(result_type: str) -> str:
        """Strip joint suffixes (_Min/_Ux/_Uy/_Uz) to base type."""
        if any(suffix in result_type for suffix in ("_Min", "_Ux", "_Uy", "_Uz")):
            return result_type.rsplit("_", 1)[0]
        return result_type
