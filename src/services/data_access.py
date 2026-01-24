"""Data access service facade for UI layer.

This service provides a clean interface between the UI and data layers,
preventing direct repository access from GUI code.

Architecture:
    GUI Layer → DataAccessService → Repositories → Database
    
Benefits:
    - Single point of data access for UI
    - Easier testing (mock the service, not 10+ repos)
    - Consistent session management
    - Clear API boundaries

Usage:
    # In GUI code
    data_service = DataAccessService(context.session_factory)
    
    # Instead of: comparison_repo = ComparisonSetRepository(session)
    comparison_sets = data_service.get_comparison_sets(project_id)
"""

from __future__ import annotations

import logging
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Callable, Dict, List, Optional, TYPE_CHECKING

from sqlalchemy.orm import Session

if TYPE_CHECKING:
    from database.models import (
        ComparisonSet,
        Element,
        LoadCase,
        Project,
        PushoverCase,
        PushoverCurvePoint,
        ResultSet,
        Story,
    )

logger = logging.getLogger(__name__)


# =============================================================================
# Data Transfer Objects (DTOs)
# =============================================================================

@dataclass
class ResultSetInfo:
    """Lightweight result set information for UI."""
    id: int
    name: str
    description: Optional[str] = None
    analysis_type: Optional[str] = None
    
    @classmethod
    def from_model(cls, model: "ResultSet") -> "ResultSetInfo":
        return cls(
            id=model.id,
            name=model.name,
            description=getattr(model, 'description', None),
            analysis_type=getattr(model, 'analysis_type', None),
        )


@dataclass
class ComparisonSetInfo:
    """Lightweight comparison set information for UI."""
    id: int
    name: str
    result_set_ids: List[int]
    result_types: List[str]
    
    @classmethod
    def from_model(cls, model: "ComparisonSet") -> "ComparisonSetInfo":
        result_set_ids = list(getattr(model, "result_set_ids", []) or [])
        if not result_set_ids and getattr(model, "result_sets", None):
            result_set_ids = [rs.id for rs in model.result_sets]
        return cls(
            id=model.id,
            name=model.name,
            result_set_ids=result_set_ids,
            result_types=list(getattr(model, "result_types", []) or []),
        )


@dataclass
class PushoverCaseInfo:
    """Lightweight pushover case information for UI."""
    id: int
    name: str
    direction: Optional[str] = None
    result_set_id: Optional[int] = None

    @classmethod
    def from_model(cls, model: "PushoverCase") -> "PushoverCaseInfo":
        return cls(
            id=model.id,
            name=model.name,
            direction=getattr(model, 'direction', None),
            result_set_id=getattr(model, 'result_set_id', None),
        )


@dataclass
class PushoverCurvePointInfo:
    """Lightweight pushover curve point for export/display."""
    step_number: int
    base_shear: float
    displacement: float

    @classmethod
    def from_model(cls, model: "PushoverCurvePoint") -> "PushoverCurvePointInfo":
        return cls(
            step_number=model.step_number,
            base_shear=model.base_shear,
            displacement=model.displacement,
        )


@dataclass
class ElementInfo:
    """Lightweight element information for UI."""
    id: int
    name: str
    element_type: str
    
    @classmethod
    def from_model(cls, model: "Element") -> "ElementInfo":
        return cls(
            id=model.id,
            name=model.name,
            element_type=model.element_type,
        )


@dataclass
class StoryInfo:
    """Lightweight story information for UI."""
    id: int
    name: str
    sort_order: int
    
    @classmethod
    def from_model(cls, model: "Story") -> "StoryInfo":
        return cls(
            id=model.id,
            name=model.name,
            sort_order=getattr(model, 'sort_order', 0),
        )


@dataclass
class LoadCaseInfo:
    """Lightweight load case information for UI."""
    id: int
    name: str
    case_type: Optional[str] = None
    
    @classmethod
    def from_model(cls, model: "LoadCase") -> "LoadCaseInfo":
        return cls(
            id=model.id,
            name=model.name,
            case_type=getattr(model, 'case_type', None),
        )


@dataclass
class ProjectInfo:
    """Lightweight project information for UI."""
    id: int
    name: str
    description: Optional[str] = None

    @classmethod
    def from_model(cls, model: "Project") -> "ProjectInfo":
        return cls(
            id=model.id,
            name=model.name,
            description=getattr(model, "description", None),
        )


# =============================================================================
# Data Access Service
# =============================================================================

class DataAccessService:
    """Facade for all data access operations used by GUI layer.
    
    This service provides a clean interface to the data layer, preventing
    direct repository access from GUI code. All operations use short-lived
    sessions for thread safety.
    
    Args:
        session_factory: Callable that returns a new SQLAlchemy session
    """
    
    def __init__(self, session_factory: Callable[[], Session]):
        self._session_factory = session_factory
    
    @contextmanager
    def _session_scope(self):
        """Provide a transactional scope around a series of operations.
        
        Automatically closes the session when done.
        """
        session = self._session_factory()
        try:
            yield session
        finally:
            session.close()
    
    # =========================================================================
    # Result Sets
    # =========================================================================
    
    def get_result_sets(self, project_id: int) -> List[ResultSetInfo]:
        """Get all result sets for a project.
        
        Args:
            project_id: Project ID
            
        Returns:
            List of ResultSetInfo DTOs
        """
        from database.repository import ResultSetRepository
        
        with self._session_scope() as session:
            repo = ResultSetRepository(session)
            result_sets = repo.get_by_project(project_id)
            return [ResultSetInfo.from_model(rs) for rs in result_sets]
    
    def get_result_set_by_id(self, result_set_id: int) -> Optional[ResultSetInfo]:
        """Get a result set by ID.
        
        Args:
            result_set_id: Result set ID
            
        Returns:
            ResultSetInfo or None if not found
        """
        from database.repository import ResultSetRepository
        
        with self._session_scope() as session:
            repo = ResultSetRepository(session)
            rs = repo.get_by_id(result_set_id)
            return ResultSetInfo.from_model(rs) if rs else None
    
    def get_result_set_names(self, result_set_ids: List[int]) -> Dict[int, str]:
        """Get names for multiple result sets.
        
        Args:
            result_set_ids: List of result set IDs
            
        Returns:
            Dict mapping ID to name
        """
        from database.repository import ResultSetRepository
        
        with self._session_scope() as session:
            repo = ResultSetRepository(session)
            names = {}
            for rs_id in result_set_ids:
                rs = repo.get_by_id(rs_id)
                if rs:
                    names[rs_id] = rs.name
            return names

    # =========================================================================
    # Projects
    # =========================================================================

    def get_project_by_name(self, name: str) -> Optional[ProjectInfo]:
        """Get a project by name within the project database.

        Args:
            name: Project name

        Returns:
            ProjectInfo or None if not found
        """
        from database.repository import ProjectRepository

        with self._session_scope() as session:
            repo = ProjectRepository(session)
            project = repo.get_by_name(name)
            return ProjectInfo.from_model(project) if project else None
    
    # =========================================================================
    # Comparison Sets
    # =========================================================================
    
    def get_comparison_sets(self, project_id: int) -> List[ComparisonSetInfo]:
        """Get all comparison sets for a project.
        
        Args:
            project_id: Project ID
            
        Returns:
            List of ComparisonSetInfo DTOs
        """
        from database.repository import ComparisonSetRepository
        
        with self._session_scope() as session:
            repo = ComparisonSetRepository(session)
            comparison_sets = repo.get_by_project(project_id)
            return [ComparisonSetInfo.from_model(cs) for cs in comparison_sets]
    
    def get_comparison_set_by_id(self, comparison_set_id: int) -> Optional[ComparisonSetInfo]:
        """Get a comparison set by ID.
        
        Args:
            comparison_set_id: Comparison set ID
            
        Returns:
            ComparisonSetInfo or None if not found
        """
        from database.repository import ComparisonSetRepository
        
        with self._session_scope() as session:
            repo = ComparisonSetRepository(session)
            cs = repo.get_by_id(comparison_set_id)
            return ComparisonSetInfo.from_model(cs) if cs else None
    
    def check_comparison_set_duplicate(self, project_id: int, name: str) -> bool:
        """Check if a comparison set name already exists.
        
        Args:
            project_id: Project ID
            name: Comparison set name to check
            
        Returns:
            True if duplicate exists
        """
        from database.repository import ComparisonSetRepository
        
        with self._session_scope() as session:
            repo = ComparisonSetRepository(session)
            return repo.check_duplicate(project_id, name)

    def create_comparison_set(
        self,
        project_id: int,
        name: str,
        result_set_ids: List[int],
        result_types: List[str],
        description: Optional[str] = None,
    ) -> ComparisonSetInfo:
        """Create a comparison set and return DTO."""
        from database.repository import ComparisonSetRepository

        with self._session_scope() as session:
            repo = ComparisonSetRepository(session)
            comparison_set = repo.create(
                project_id=project_id,
                name=name,
                result_set_ids=result_set_ids,
                result_types=result_types,
                description=description,
            )
            session.commit()
            return ComparisonSetInfo.from_model(comparison_set)
    
    # =========================================================================
    # Pushover Cases
    # =========================================================================
    
    def get_pushover_cases(self, result_set_id: int) -> List[PushoverCaseInfo]:
        """Get all pushover cases for a result set.
        
        Args:
            result_set_id: Result set ID
            
        Returns:
            List of PushoverCaseInfo DTOs
        """
        from database.repository import PushoverCaseRepository
        
        with self._session_scope() as session:
            repo = PushoverCaseRepository(session)
            cases = repo.get_by_result_set(result_set_id)
            return [PushoverCaseInfo.from_model(c) for c in cases]
    
    def get_pushover_case_by_name(
        self,
        project_id: int,
        result_set_id: int,
        name: str,
    ) -> Optional[PushoverCaseInfo]:
        """Get a pushover case by name within a result set.

        Args:
            project_id: Project ID
            result_set_id: Result set ID
            name: Case name

        Returns:
            PushoverCaseInfo or None if not found
        """
        from database.repository import PushoverCaseRepository

        with self._session_scope() as session:
            repo = PushoverCaseRepository(session)
            case = repo.get_by_name(project_id, result_set_id, name)
            return PushoverCaseInfo.from_model(case) if case else None
    
    def get_pushover_cases_by_result_sets(
        self,
        result_set_ids: List[int]
    ) -> Dict[int, List[PushoverCaseInfo]]:
        """Get pushover cases for multiple result sets.
        
        Args:
            result_set_ids: List of result set IDs
            
        Returns:
            Dict mapping result_set_id to list of PushoverCaseInfo
        """
        from database.repository import PushoverCaseRepository
        
        with self._session_scope() as session:
            repo = PushoverCaseRepository(session)
            result = {}
            for rs_id in result_set_ids:
                cases = repo.get_by_result_set(rs_id)
                result[rs_id] = [PushoverCaseInfo.from_model(c) for c in cases]
            return result

    def get_pushover_curve_data(
        self,
        pushover_case_id: int
    ) -> List["PushoverCurvePointInfo"]:
        """Get curve data points for a pushover case.

        Args:
            pushover_case_id: Pushover case ID

        Returns:
            List of PushoverCurvePointInfo DTOs ordered by step number
        """
        from database.repository import PushoverCaseRepository

        with self._session_scope() as session:
            repo = PushoverCaseRepository(session)
            points = repo.get_curve_data(pushover_case_id)
            return [PushoverCurvePointInfo.from_model(pt) for pt in points]

    # =========================================================================
    # Elements
    # =========================================================================
    
    def get_element_by_id(self, element_id: int) -> Optional[ElementInfo]:
        """Get an element by ID.
        
        Args:
            element_id: Element ID
            
        Returns:
            ElementInfo or None if not found
        """
        from database.repository import ElementRepository
        
        with self._session_scope() as session:
            repo = ElementRepository(session)
            element = repo.get_by_id(element_id)
            return ElementInfo.from_model(element) if element else None
    
    def get_elements_by_type(
        self,
        project_id: int,
        element_type: str
    ) -> List[ElementInfo]:
        """Get all elements of a specific type for a project.
        
        Args:
            project_id: Project ID
            element_type: Element type ("Wall", "Column", "Beam", "Quad")
            
        Returns:
            List of ElementInfo DTOs
        """
        from database.repository import ElementRepository
        
        with self._session_scope() as session:
            repo = ElementRepository(session)
            elements = repo.get_by_project_and_type(project_id, element_type)
            return [ElementInfo.from_model(e) for e in elements]

    def get_elements(self, project_id: int) -> List[ElementInfo]:
        """Get all elements for a project."""
        from database.repository import ElementRepository

        with self._session_scope() as session:
            repo = ElementRepository(session)
            elements = repo.get_by_project(project_id)
            return [ElementInfo.from_model(e) for e in elements]
    
    # =========================================================================
    # Stories
    # =========================================================================
    
    def get_stories(self, project_id: int) -> List[StoryInfo]:
        """Get all stories for a project.
        
        Args:
            project_id: Project ID
            
        Returns:
            List of StoryInfo DTOs ordered by sort_order
        """
        from database.repository import StoryRepository
        
        with self._session_scope() as session:
            repo = StoryRepository(session)
            stories = repo.get_by_project(project_id)
            return [StoryInfo.from_model(s) for s in stories]
    
    # =========================================================================
    # Load Cases
    # =========================================================================
    
    def get_load_cases(self, project_id: int) -> List[LoadCaseInfo]:
        """Get all load cases for a project.
        
        Args:
            project_id: Project ID
            
        Returns:
            List of LoadCaseInfo DTOs
        """
        from database.repository import LoadCaseRepository
        
        with self._session_scope() as session:
            repo = LoadCaseRepository(session)
            load_cases = repo.get_by_project(project_id)
            return [LoadCaseInfo.from_model(lc) for lc in load_cases]
    
    # =========================================================================
    # Time Series
    # =========================================================================
    
    def get_time_series_load_cases(
        self,
        project_id: int,
        result_set_ids: List[int]
    ) -> Dict[int, List[str]]:
        """Get time series load case names for multiple result sets.
        
        Args:
            project_id: Project ID
            result_set_ids: List of result set IDs
            
        Returns:
            Dict mapping result_set_id to list of load case names
        """
        from processing.time_history_importer import TimeSeriesRepository
        
        with self._session_scope() as session:
            repo = TimeSeriesRepository(session)
            result = {}
            for rs_id in result_set_ids:
                # Get unique load case names for this result set
                load_cases = repo.get_available_load_cases(project_id, rs_id)
                result[rs_id] = load_cases
            return result

    def get_time_series_entries(
        self,
        project_id: int,
        result_set_id: int,
        load_case_name: str,
        result_type: str,
        direction: str,
    ) -> List[object]:
        """Get raw time series entries for plotting (short-lived session)."""
        from processing.time_history_importer import TimeSeriesRepository

        with self._session_scope() as session:
            repo = TimeSeriesRepository(session)
            return repo.get_time_series(
                project_id=project_id,
                result_set_id=result_set_id,
                load_case_name=load_case_name,
                result_type=result_type,
                direction=direction,
            )
    
    # =========================================================================
    # Projects (Catalog)
    # =========================================================================
    
    def check_project_name_exists(self, name: str) -> bool:
        """Check if a project name already exists in the catalog.

        Args:
            name: Project name to check

        Returns:
            True if project with name exists
        """
        from database.repository import CatalogProjectRepository
        from database.session import get_catalog_session

        with get_catalog_session() as session:
            repo = CatalogProjectRepository(session)
            existing = repo.get_by_name(name)
            return existing is not None

    # =========================================================================
    # Cache Type Discovery (for export dialogs, comparison dialogs, etc.)
    # =========================================================================

    def get_available_global_types(self, result_set_ids: List[int]) -> List[str]:
        """Get distinct global result types available in the cache.

        Args:
            result_set_ids: List of result set IDs to query

        Returns:
            List of distinct result type strings
        """
        from database.models import GlobalResultsCache

        with self._session_scope() as session:
            types = (
                session.query(GlobalResultsCache.result_type)
                .filter(GlobalResultsCache.result_set_id.in_(result_set_ids))
                .distinct()
                .all()
            )
            return [t[0] for t in types]

    def get_available_element_types(self, result_set_ids: List[int]) -> List[str]:
        """Get distinct element result types available in the cache.

        Args:
            result_set_ids: List of result set IDs to query

        Returns:
            List of distinct result type strings
        """
        from database.models import ElementResultsCache

        with self._session_scope() as session:
            types = (
                session.query(ElementResultsCache.result_type)
                .filter(ElementResultsCache.result_set_id.in_(result_set_ids))
                .distinct()
                .all()
            )
            return [t[0] for t in types]

    def get_available_joint_types(self, result_set_ids: List[int]) -> List[str]:
        """Get distinct joint result types available in the cache.

        Args:
            result_set_ids: List of result set IDs to query

        Returns:
            List of distinct result type strings
        """
        from database.models import JointResultsCache

        with self._session_scope() as session:
            types = (
                session.query(JointResultsCache.result_type)
                .filter(JointResultsCache.result_set_id.in_(result_set_ids))
                .distinct()
                .all()
            )
            return [t[0] for t in types]

    def has_time_series(self, result_set_id: int) -> bool:
        """Check if a result set has time series data.

        Args:
            result_set_id: Result set ID

        Returns:
            True if time series data exists
        """
        from database.models import TimeSeriesGlobalCache

        with self._session_scope() as session:
            exists = (
                session.query(TimeSeriesGlobalCache.id)
                .filter(TimeSeriesGlobalCache.result_set_id == result_set_id)
                .first()
            )
            return exists is not None

    def get_pushover_result_sets(self, project_id: int) -> List[ResultSetInfo]:
        """Get all pushover-type result sets for a project.

        Args:
            project_id: Project ID

        Returns:
            List of ResultSetInfo DTOs for pushover analysis
        """
        from database.models import ResultSet

        with self._session_scope() as session:
            result_sets = (
                session.query(ResultSet)
                .filter(
                    ResultSet.project_id == project_id,
                    ResultSet.analysis_type == "Pushover"
                )
                .all()
            )
            return [ResultSetInfo.from_model(rs) for rs in result_sets]

    def get_result_set_by_name(
        self,
        project_id: int,
        name: str
    ) -> Optional[ResultSetInfo]:
        """Get a result set by name within a project.

        Args:
            project_id: Project ID
            name: Result set name

        Returns:
            ResultSetInfo or None if not found
        """
        from database.models import ResultSet

        with self._session_scope() as session:
            rs = (
                session.query(ResultSet)
                .filter(
                    ResultSet.project_id == project_id,
                    ResultSet.name == name
                )
                .first()
            )
            return ResultSetInfo.from_model(rs) if rs else None

    def get_global_cache_with_matrix(
        self,
        result_set_id: int
    ) -> List[tuple]:
        """Get global cache entries with result matrices for report building.

        Args:
            result_set_id: Result set ID

        Returns:
            List of (result_type, results_matrix) tuples
        """
        from database.models import GlobalResultsCache

        with self._session_scope() as session:
            results = (
                session.query(
                    GlobalResultsCache.result_type,
                    GlobalResultsCache.results_matrix
                )
                .filter(GlobalResultsCache.result_set_id == result_set_id)
                .all()
            )
            return list(results)

    def get_available_element_types_for_result_set(
        self,
        result_set_id: int
    ) -> List[str]:
        """Get distinct element result types for a single result set.

        Args:
            result_set_id: Result set ID

        Returns:
            List of distinct result type strings
        """
        from database.models import ElementResultsCache

        with self._session_scope() as session:
            types = (
                session.query(ElementResultsCache.result_type)
                .filter(ElementResultsCache.result_set_id == result_set_id)
                .distinct()
                .all()
            )
            return [t[0] for t in types]

    def get_available_joint_types_for_result_set(
        self,
        result_set_id: int
    ) -> List[str]:
        """Get distinct joint result types for a single result set.

        Args:
            result_set_id: Result set ID

        Returns:
            List of distinct result type strings
        """
        from database.models import JointResultsCache

        with self._session_scope() as session:
            types = (
                session.query(JointResultsCache.result_type)
                .filter(JointResultsCache.result_set_id == result_set_id)
                .distinct()
                .all()
            )
            return [t[0] for t in types]
