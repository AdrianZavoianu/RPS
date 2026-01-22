"""
Base class for Pushover Joint Importers

Provides common functionality for importing pushover joint-level results
(joint displacements, soil pressures, vertical displacements) into JointResultsCache.
"""

import logging
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Callable, Dict, List, Optional, Set, Any

import pandas as pd
from sqlalchemy.orm import Session

from database.models import (
    ResultSet,
    LoadCase,
    JointResultsCache,
)

logger = logging.getLogger(__name__)


class BasePushoverJointImporter(ABC):
    """Base class for pushover joint result importers.

    Subclasses must implement:
    - _create_parser(): Return the appropriate parser instance
    - _get_result_types(): Return list of result type strings to cache
    - _import_direction(): Import data for one direction
    - _build_cache(): Build JointResultsCache entries
    - _get_stats_template(): Return initial stats dictionary
    """

    def __init__(
        self,
        project_id: int,
        session: Session,
        result_set_id: int,
        file_path: Path,
        selected_load_cases_x: List[str],
        selected_load_cases_y: List[str],
        progress_callback: Optional[Callable[[str, int, int], None]] = None,
    ):
        """Initialize importer.

        Args:
            project_id: ID of the project
            session: Database session
            result_set_id: ID of the result set to add results to
            file_path: Path to Excel file containing results
            selected_load_cases_x: List of selected load cases for X direction
            selected_load_cases_y: List of selected load cases for Y direction
            progress_callback: Optional callback for progress updates
        """
        self.project_id = project_id
        self.session = session
        self.result_set_id = result_set_id
        self.file_path = file_path
        self.selected_load_cases_x = set(selected_load_cases_x)
        self.selected_load_cases_y = set(selected_load_cases_y)
        self.progress_callback = progress_callback

        self.result_set: Optional[ResultSet] = None
        self.load_cases_cache: Dict[str, LoadCase] = {}

    def import_all(self) -> Dict:
        """Import all results for this joint type.

        Returns:
            Dict with import statistics
        """
        try:
            self._log_progress("Loading result set...", 0, 100)

            # Get existing result set
            self.result_set = self.session.query(ResultSet).get(self.result_set_id)
            if not self.result_set:
                raise ValueError(f"Result set ID {self.result_set_id} not found")

            # Check required sheets
            if not self._validate_required_sheets():
                return self._get_stats_template()

            stats = self._get_stats_template()
            parser = self._create_parser()

            # Import X direction
            if self.selected_load_cases_x:
                self._log_progress("Importing X direction...", 30, 100)
                x_stats = self._import_direction(parser, 'X', self.selected_load_cases_x)
                self._merge_stats(stats, x_stats, 'x')

            # Import Y direction
            if self.selected_load_cases_y:
                self._log_progress("Importing Y direction...", 60, 100)
                y_stats = self._import_direction(parser, 'Y', self.selected_load_cases_y)
                self._merge_stats(stats, y_stats, 'y')

            # Build cache
            self._log_progress("Building cache...", 90, 100)
            self._build_cache()

            self._log_progress("Import complete!", 100, 100)
            self.session.commit()

            return stats

        except Exception as e:
            self.session.rollback()
            logger.exception(f"{self.__class__.__name__} import failed")
            raise

    @abstractmethod
    def _create_parser(self) -> Any:
        """Create and return the parser instance for this importer."""
        pass

    @abstractmethod
    def _get_result_types(self) -> List[str]:
        """Return list of result type strings used by this importer."""
        pass

    @abstractmethod
    def _get_stats_template(self) -> Dict:
        """Return initial stats dictionary template."""
        pass

    @abstractmethod
    def _import_direction(self, parser: Any, direction: str, selected_load_cases: Set[str]) -> Dict:
        """Import data for one direction.

        Args:
            parser: Parser instance
            direction: 'X' or 'Y'
            selected_load_cases: Set of load cases to import

        Returns:
            Dict with direction-specific counts
        """
        pass

    @abstractmethod
    def _build_cache(self) -> None:
        """Build JointResultsCache entries from imported data."""
        pass

    def _validate_required_sheets(self) -> bool:
        """Validate that required sheets exist. Override if needed.

        Returns:
            True if all required sheets exist, False otherwise
        """
        return True

    def _merge_stats(self, stats: Dict, direction_stats: Dict, prefix: str) -> None:
        """Merge direction stats into main stats dict.

        Default implementation prefixes keys with 'x_' or 'y_'.
        Override for custom behavior.
        """
        for key, value in direction_stats.items():
            stats_key = f"{prefix}_{key}"
            if stats_key in stats:
                stats[stats_key] += value

    def _get_or_create_load_case(self, load_case_name: str) -> LoadCase:
        """Get or create load case."""
        if load_case_name in self.load_cases_cache:
            return self.load_cases_cache[load_case_name]

        load_case = self.session.query(LoadCase).filter(
            LoadCase.project_id == self.project_id,
            LoadCase.name == load_case_name
        ).first()

        if not load_case:
            load_case = LoadCase(
                project_id=self.project_id,
                name=load_case_name,
                case_type="Pushover"
            )
            self.session.add(load_case)
            self.session.flush()

        self.load_cases_cache[load_case_name] = load_case
        return load_case

    def _delete_existing_cache(self, result_types: List[str]) -> None:
        """Delete existing cache entries for specified result types."""
        self.session.query(JointResultsCache).filter(
            JointResultsCache.result_set_id == self.result_set_id,
            JointResultsCache.result_type.in_(result_types)
        ).delete(synchronize_session=False)

    def _create_cache_entry(
        self,
        shell_object: str,
        unique_name: str,
        result_type: str,
        results_matrix: Dict
    ) -> JointResultsCache:
        """Create a JointResultsCache entry."""
        return JointResultsCache(
            project_id=self.project_id,
            result_set_id=self.result_set_id,
            shell_object=shell_object,
            unique_name=unique_name,
            result_type=result_type,
            results_matrix=results_matrix
        )

    def _log_progress(self, message: str, current: int, total: int) -> None:
        """Log progress message."""
        if self.progress_callback:
            self.progress_callback(message, current, total)
        logger.info(f"{message} ({current}/{total})")
