"""Pushover data importer - orchestrates parsing and transformation."""

import logging
from pathlib import Path
from typing import Optional
from sqlalchemy.orm import Session

from database.models import Project, ResultSet
from database.repositories import ProjectRepository, ResultSetRepository
from .pushover_curve_parser import PushoverParser
from .pushover_transformer import PushoverTransformer


logger = logging.getLogger(__name__)


class PushoverImporter:
    """Imports pushover curve data from Excel files."""

    def __init__(self, session: Session):
        self.session = session
        self.project_repo = ProjectRepository(session)
        self.result_set_repo = ResultSetRepository(session)

    def import_pushover_file(
        self,
        file_path: str | Path,
        project_id: int,
        result_set_name: str,
        base_story: str,
        direction: str = None,
        overwrite: bool = False
    ) -> dict:
        """
        Import pushover curve data from Excel file for a specific direction.

        Args:
            file_path: Path to Excel file
            project_id: Project ID
            result_set_name: Name for the result set (e.g., 'PUSH_X', 'PUSH_Y')
            base_story: Base story for shear extraction
            direction: Direction to filter ('X' or 'Y'). If None, import all
            overwrite: If True, delete existing data before import

        Returns:
            Dict with import statistics
        """
        logger.info(f"Starting pushover import: {file_path} (direction: {direction})")
        file_path = Path(file_path)

        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        # Get or create result set
        result_set = self._get_or_create_result_set(
            project_id, result_set_name, overwrite
        )

        # Parse Excel file
        logger.info("Parsing pushover curves...")
        parser = PushoverParser(file_path)
        all_curves = parser.parse_curves(base_story)

        # Filter curves by direction if specified
        if direction:
            curves = {name: curve for name, curve in all_curves.items()
                     if curve.direction == direction}
            logger.info(f"Filtered to {len(curves)} curves for direction {direction}")
        else:
            curves = all_curves
            logger.info(f"Parsed {len(curves)} pushover curves (all directions)")

        if not curves:
            raise ValueError(f"No curves found for direction '{direction}' in the Excel file")

        # Transform to ORM models
        logger.info("Transforming to database models...")
        transformer = PushoverTransformer(self.session)

        if overwrite:
            transformer.delete_existing_cases(project_id, result_set.id)

        pushover_cases = transformer.transform_curves(
            curves, project_id, result_set.id, base_story
        )

        # Save to database
        logger.info("Saving to database...")
        transformer.save_pushover_cases(pushover_cases)

        stats = {
            'result_set_id': result_set.id,
            'result_set_name': result_set.name,
            'direction': direction,
            'curves_imported': len(curves),
            'total_points': sum(len(case.curve_points) for case in pushover_cases)
        }

        logger.info(f"Pushover import completed: {stats}")
        return stats

    def _get_or_create_result_set(
        self,
        project_id: int,
        result_set_name: str,
        overwrite: bool
    ) -> ResultSet:
        """Get existing or create new result set for pushover data."""
        # Check if result set exists
        exists = self.result_set_repo.check_duplicate(project_id, result_set_name)

        if exists and not overwrite:
            raise ValueError(
                f"Result set '{result_set_name}' already exists. "
                f"Use overwrite=True to replace."
            )

        if exists:
            logger.info(f"Overwriting existing result set: {result_set_name}")

        # Get or create result set
        result_set = self.result_set_repo.get_or_create(project_id, result_set_name)

        # Update analysis_type to Pushover
        result_set.analysis_type = 'Pushover'
        result_set.description = "Pushover analysis results"
        self.session.commit()

        return result_set

    def get_available_stories(self, file_path: str | Path) -> list[str]:
        """Get list of available stories from Excel file (for UI selection)."""
        parser = PushoverParser(file_path)
        return parser.get_available_stories()
