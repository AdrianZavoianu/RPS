"""Importer for time-history data into the database.

Handles importing parsed time series data into the TimeSeriesGlobalCache table.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Callable, List, Optional, Set

from sqlalchemy.orm import Session

from database.models import (
    Project,
    ResultSet,
    Story,
    TimeSeriesGlobalCache,
)
from database.repository import StoryRepository

from .time_history_parser import TimeHistoryParser, TimeHistoryParseResult, TimeSeriesData

logger = logging.getLogger(__name__)


class TimeHistoryImporter:
    """Imports time history data into the database."""

    def __init__(
        self,
        session: Session,
        project_id: int,
        result_set_id: int,
        progress_callback: Optional[Callable[[int, str], None]] = None,
    ):
        self.session = session
        self.project_id = project_id
        self.result_set_id = result_set_id
        self.progress_callback = progress_callback

        self._story_lookup: dict[str, int] = {}
        self._story_repo = StoryRepository(session)

    def import_file(
        self,
        file_path: str | Path,
        selected_load_cases: Optional[Set[str]] = None,
    ) -> int:
        """Import a single time history file.

        Args:
            file_path: Path to the Excel file
            selected_load_cases: Optional set of load case names to import.
                                 If None, imports all load cases found.

        Returns:
            Number of time series records imported
        """
        self._report_progress(0, "Parsing time history file...")

        parser = TimeHistoryParser(file_path)
        result = parser.parse()

        # Check if the load case should be imported
        if selected_load_cases and result.load_case_name not in selected_load_cases:
            self._report_progress(100, f"Skipping load case '{result.load_case_name}' (not selected)")
            return 0

        self._report_progress(20, f"Creating stories for {result.load_case_name}...")
        self._ensure_stories(result.stories)

        self._report_progress(30, "Importing drifts...")
        count = 0
        count += self._import_series(result.drifts_x, result.load_case_name, "Drifts", "X")
        count += self._import_series(result.drifts_y, result.load_case_name, "Drifts", "Y")

        self._report_progress(50, "Importing forces...")
        count += self._import_series(result.forces_x, result.load_case_name, "Forces", "X")
        count += self._import_series(result.forces_y, result.load_case_name, "Forces", "Y")

        self._report_progress(70, "Importing displacements...")
        count += self._import_series(result.displacements_x, result.load_case_name, "Displacements", "X")
        count += self._import_series(result.displacements_y, result.load_case_name, "Displacements", "Y")

        self._report_progress(85, "Importing accelerations...")
        count += self._import_series(result.accelerations_x, result.load_case_name, "Accelerations", "X")
        count += self._import_series(result.accelerations_y, result.load_case_name, "Accelerations", "Y")

        self._report_progress(95, "Committing to database...")
        self.session.commit()

        self._report_progress(100, f"Imported {count} time series records for {result.load_case_name}")
        return count

    def _ensure_stories(self, story_names: List[str]) -> None:
        """Ensure all stories exist in the database and build lookup."""
        existing_stories = self._story_repo.get_by_project(self.project_id)
        existing_lookup = {s.name: s.id for s in existing_stories}

        for idx, name in enumerate(story_names):
            if name in existing_lookup:
                self._story_lookup[name] = existing_lookup[name]
            else:
                # Create new story
                story = Story(
                    project_id=self.project_id,
                    name=name,
                    sort_order=idx,
                )
                self.session.add(story)
                self.session.flush()
                self._story_lookup[name] = story.id

    def _import_series(
        self,
        series_list: List[TimeSeriesData],
        load_case_name: str,
        result_type: str,
        direction: str,
    ) -> int:
        """Import a list of time series for a result type.

        Args:
            series_list: List of TimeSeriesData objects
            load_case_name: Name of the load case (e.g., 'TH02')
            result_type: Type of result ('Drifts', 'Forces', etc.)
            direction: Direction ('X' or 'Y')

        Returns:
            Number of records imported
        """
        count = 0

        for series in series_list:
            story_id = self._story_lookup.get(series.story)
            if not story_id:
                logger.warning(f"Story '{series.story}' not found in lookup, skipping")
                continue

            # Check if entry already exists
            existing = self.session.query(TimeSeriesGlobalCache).filter_by(
                project_id=self.project_id,
                result_set_id=self.result_set_id,
                load_case_name=load_case_name,
                result_type=result_type,
                direction=direction,
                story_id=story_id,
            ).first()

            if existing:
                # Update existing entry
                existing.time_steps = series.time_steps
                existing.values = series.values
                existing.story_sort_order = series.story_sort_order
            else:
                # Create new entry
                cache_entry = TimeSeriesGlobalCache(
                    project_id=self.project_id,
                    result_set_id=self.result_set_id,
                    load_case_name=load_case_name,
                    result_type=result_type,
                    direction=direction,
                    story_id=story_id,
                    time_steps=series.time_steps,
                    values=series.values,
                    story_sort_order=series.story_sort_order,
                )
                self.session.add(cache_entry)

            count += 1

        return count

    def _report_progress(self, percent: int, message: str) -> None:
        """Report progress to callback if available."""
        if self.progress_callback:
            self.progress_callback(percent, message)
        logger.debug(f"Import progress: {percent}% - {message}")


class TimeSeriesRepository:
    """Repository for querying time series data."""

    def __init__(self, session: Session):
        self.session = session

    def get_available_load_cases(
        self,
        project_id: int,
        result_set_id: int,
    ) -> List[str]:
        """Get all available load case names for a result set."""
        result = self.session.query(TimeSeriesGlobalCache.load_case_name).filter_by(
            project_id=project_id,
            result_set_id=result_set_id,
        ).distinct().all()

        return [r[0] for r in result]

    def get_available_result_types(
        self,
        project_id: int,
        result_set_id: int,
        load_case_name: str,
    ) -> List[str]:
        """Get all available result types for a load case."""
        result = self.session.query(TimeSeriesGlobalCache.result_type).filter_by(
            project_id=project_id,
            result_set_id=result_set_id,
            load_case_name=load_case_name,
        ).distinct().all()

        return [r[0] for r in result]

    def get_time_series(
        self,
        project_id: int,
        result_set_id: int,
        load_case_name: str,
        result_type: str,
        direction: str,
    ) -> List[TimeSeriesGlobalCache]:
        """Get time series data for all stories.

        Returns entries sorted by story_sort_order descending (lowest floor first).
        In ETABS exports, stories appear top-to-bottom, so sort_order=0 is Roof.
        Descending order gives us Ground (highest sort_order) first for plotting.
        """
        return self.session.query(TimeSeriesGlobalCache).filter_by(
            project_id=project_id,
            result_set_id=result_set_id,
            load_case_name=load_case_name,
            result_type=result_type,
            direction=direction,
        ).order_by(TimeSeriesGlobalCache.story_sort_order.desc()).all()

    def has_time_series(self, project_id: int, result_set_id: int) -> bool:
        """Check if a result set has any time series data."""
        return self.session.query(TimeSeriesGlobalCache).filter_by(
            project_id=project_id,
            result_set_id=result_set_id,
        ).first() is not None

    def delete_time_series(self, project_id: int, result_set_id: int) -> int:
        """Delete all time series data for a result set.

        Returns number of records deleted.
        """
        count = self.session.query(TimeSeriesGlobalCache).filter_by(
            project_id=project_id,
            result_set_id=result_set_id,
        ).delete()
        self.session.commit()
        return count
