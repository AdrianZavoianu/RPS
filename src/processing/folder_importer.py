"""Folder-based batch importer for processing multiple Excel files."""

from pathlib import Path
from typing import List, Dict, Any, Optional, Callable
import pandas as pd
from collections import defaultdict

from database.base import get_session
from database.repository import (
    ProjectRepository,
    LoadCaseRepository,
    StoryRepository,
    ResultRepository,
    CacheRepository,
    ResultSetRepository,
    ResultCategoryRepository,
    AbsoluteMaxMinDriftRepository,
)
from database.models import StoryDrift

from .excel_parser import ExcelParser


class FolderImporter:
    """Import structural analysis results from a folder containing multiple Excel files."""

    def __init__(
        self,
        folder_path: str,
        project_name: str,
        result_set_name: str,
        result_types: Optional[List[str]] = None,
        progress_callback: Optional[Callable[[str, int, int], None]] = None,
    ):
        """Initialize folder importer.

        Args:
            folder_path: Path to folder containing Excel files
            project_name: Name of the project
            result_set_name: Name for this result set (e.g., DES, MCE, SLE)
            result_types: List of result types to import (default: ['Story Drifts'])
            progress_callback: Optional callback function(message, current, total)
        """
        self.folder_path = Path(folder_path)
        if not self.folder_path.exists() or not self.folder_path.is_dir():
            raise ValueError(f"Invalid folder path: {folder_path}")

        self.project_name = project_name
        self.result_set_name = result_set_name
        self.result_types = result_types or ["Story Drifts"]
        self.progress_callback = progress_callback

        # Find all Excel files in folder
        self.excel_files = self._find_excel_files()

    def _find_excel_files(self) -> List[Path]:
        """Find all Excel files in the folder."""
        excel_files = []
        for pattern in ["*.xlsx", "*.xls"]:
            excel_files.extend(self.folder_path.glob(pattern))

        # Filter out temporary files
        excel_files = [f for f in excel_files if not f.name.startswith("~$")]

        return sorted(excel_files)

    def _report_progress(self, message: str, current: int, total: int):
        """Report progress if callback is provided."""
        if self.progress_callback:
            self.progress_callback(message, current, total)

    def import_all(self) -> Dict[str, Any]:
        """Import all available data from all Excel files in folder.

        Returns:
            Dictionary with import statistics
        """
        if not self.excel_files:
            raise ValueError(f"No Excel files found in folder: {self.folder_path}")

        session = get_session()
        stats = {
            "project": None,
            "files_processed": 0,
            "files_total": len(self.excel_files),
            "load_cases": set(),
            "stories": set(),
            "drifts": 0,
            "errors": [],
        }

        try:
            # Create or get project
            project_repo = ProjectRepository(session)
            project = project_repo.get_by_name(self.project_name)

            if not project:
                project = project_repo.create(
                    name=self.project_name,
                    description=f"Batch imported from {self.folder_path.name}",
                )
            stats["project"] = project.name

            # Create or get result set
            result_set_repo = ResultSetRepository(session)
            result_set = result_set_repo.get_or_create(
                project_id=project.id,
                name=self.result_set_name,
            )

            # Create result category (Envelopes → Global)
            category_repo = ResultCategoryRepository(session)
            result_category = category_repo.get_or_create(
                result_set_id=result_set.id,
                category_name="Envelopes",
                category_type="Global",
            )

            # Store for use in import methods
            self.result_category_id = result_category.id
            self.result_set_id = result_set.id

            self._report_progress("Processing files...", 0, len(self.excel_files))

            # Process each Excel file
            for idx, excel_file in enumerate(self.excel_files, 1):
                try:
                    self._report_progress(
                        f"Processing {excel_file.name}...", idx, len(self.excel_files)
                    )

                    # Import Story Drifts from this file
                    if "Story Drifts" in self.result_types:
                        file_stats = self._import_story_drifts_from_file(
                            session, project.id, excel_file
                        )
                        stats["drifts"] += file_stats.get("drifts", 0)
                        stats["load_cases"].update(file_stats.get("load_cases", []))
                        stats["stories"].update(file_stats.get("stories", []))

                    stats["files_processed"] += 1

                except Exception as e:
                    error_msg = f"Error processing {excel_file.name}: {str(e)}"
                    stats["errors"].append(error_msg)
                    print(error_msg)  # Log to console
                    continue

            # Generate cache after all imports
            self._report_progress("Generating cache...", len(self.excel_files), len(self.excel_files))
            self._generate_cache(session, project.id, self.result_set_id)

            session.commit()

            # Convert sets to counts
            stats["load_cases"] = len(stats["load_cases"])
            stats["stories"] = len(stats["stories"])

        except Exception as e:
            session.rollback()
            stats["errors"].append(str(e))
            raise
        finally:
            session.close()

        return stats

    def _import_story_drifts_from_file(
        self, session, project_id: int, excel_file: Path
    ) -> Dict[str, Any]:
        """Import story drift data from a single Excel file."""
        stats = {"load_cases": set(), "stories": set(), "drifts": 0}

        try:
            parser = ExcelParser(str(excel_file))

            # Check if Story Drifts sheet exists
            if not parser.validate_sheet_exists("Story Drifts"):
                return stats

            # Parse data
            df, load_cases, stories = parser.get_story_drifts()

            # Create/get repositories
            case_repo = LoadCaseRepository(session)
            story_repo = StoryRepository(session)
            result_repo = ResultRepository(session)

            # Process each direction
            from processing.result_processor import ResultProcessor

            for direction in ["X", "Y"]:
                # Process data
                processed = ResultProcessor.process_story_drifts(
                    df, load_cases, stories, direction
                )

                # Store in database
                drift_objects = []

                for _, row in processed.iterrows():
                    # Get or create story
                    story = story_repo.get_or_create(
                        project_id=project_id,
                        name=row["Story"],
                        sort_order=(
                            stories.index(row["Story"]) if row["Story"] in stories else None
                        ),
                    )

                    # Get or create load case (include file name in load case name for uniqueness)
                    file_prefix = excel_file.stem  # Filename without extension
                    load_case_name = f"{file_prefix}_{row['LoadCase']}"

                    load_case = case_repo.get_or_create(
                        project_id=project_id,
                        name=load_case_name,
                        case_type="Time History",
                    )

                    # Create drift object
                    drift = StoryDrift(
                        story_id=story.id,
                        load_case_id=load_case.id,
                        result_category_id=self.result_category_id,
                        direction=direction,
                        drift=row["Drift"],
                        max_drift=row.get("MaxDrift"),
                        min_drift=row.get("MinDrift"),
                    )
                    drift_objects.append(drift)

                    stats["load_cases"].add(load_case_name)
                    stats["stories"].add(row["Story"])

                # Bulk insert
                if drift_objects:
                    result_repo.bulk_create_drifts(drift_objects)
                    stats["drifts"] += len(drift_objects)

        except Exception as e:
            raise ValueError(f"Error importing story drifts from {excel_file.name}: {e}")

        return stats

    def _generate_cache(self, session, project_id: int, result_set_id: int):
        """Generate wide-format cache tables for fast tabular display."""
        story_repo = StoryRepository(session)
        cache_repo = CacheRepository(session)
        abs_maxmin_repo = AbsoluteMaxMinDriftRepository(session)

        # Get all stories for this project
        stories = story_repo.get_by_project(project_id)

        # Generate cache for Story Drifts
        self._cache_drifts(session, project_id, result_set_id, stories, cache_repo)

        # Calculate and store absolute max/min drifts
        self._calculate_absolute_maxmin(session, project_id, result_set_id, abs_maxmin_repo)

    def _cache_drifts(self, session, project_id: int, result_set_id: int, stories, cache_repo):
        """Generate cache for story drifts."""
        from database.models import StoryDrift, LoadCase, Story

        # Get all drifts for this project and result set
        drifts = (
            session.query(StoryDrift, LoadCase.name)
            .join(LoadCase, StoryDrift.load_case_id == LoadCase.id)
            .join(Story, StoryDrift.story_id == Story.id)
            .filter(Story.project_id == project_id)
            .filter(StoryDrift.result_category_id == self.result_category_id)
            .all()
        )

        # Group by story and build wide-format matrix
        story_matrices = {}
        for drift, load_case_name in drifts:
            story_id = drift.story_id
            if story_id not in story_matrices:
                story_matrices[story_id] = {}

            # Key format: LoadCase_Direction (e.g., File1_TH01_X)
            key = f"{load_case_name}_{drift.direction}"
            story_matrices[story_id][key] = drift.drift

        # Upsert cache entries
        for story_id, results_matrix in story_matrices.items():
            cache_repo.upsert_cache_entry(
                project_id=project_id,
                story_id=story_id,
                result_type="Drifts",
                results_matrix=results_matrix,
                result_set_id=result_set_id,
            )

    def get_file_list(self) -> List[str]:
        """Get list of Excel files to be processed.

        Returns:
            List of filenames
        """
        return [f.name for f in self.excel_files]

    def get_file_count(self) -> int:
        """Get count of Excel files to be processed.

        Returns:
            Number of files
        """
        return len(self.excel_files)

    def _calculate_absolute_maxmin(self, session, project_id: int, result_set_id: int, abs_maxmin_repo):
        """Calculate and store absolute maximum drifts from Max/Min comparison.
        
        Args:
            session: Database session
            project_id: Project ID
            result_set_id: Result set ID
            abs_maxmin_repo: AbsoluteMaxMinDriftRepository instance
        """
        from database.models import StoryDrift, LoadCase, Story
        
        # Get all drifts for this project and result set
        drifts = (
            session.query(StoryDrift, LoadCase, Story)
            .join(LoadCase, StoryDrift.load_case_id == LoadCase.id)
            .join(Story, StoryDrift.story_id == Story.id)
            .filter(Story.project_id == project_id)
            .filter(StoryDrift.result_category_id == self.result_category_id)
            .all()
        )
        
        # Group by story, load case, direction and calculate absolute max
        drift_records = []
        
        for drift_obj, load_case, story in drifts:
            # Get max and min values
            max_val = drift_obj.max_drift if drift_obj.max_drift is not None else drift_obj.drift
            min_val = drift_obj.min_drift if drift_obj.min_drift is not None else drift_obj.drift
            
            # Calculate absolute maximum
            abs_max = abs(max_val)
            abs_min = abs(min_val)
            
            if abs_max >= abs_min:
                absolute_max_drift = abs_max
                sign = 'positive'
            else:
                absolute_max_drift = abs_min
                sign = 'negative'
            
            # Create record
            drift_records.append({
                'project_id': project_id,
                'result_set_id': result_set_id,
                'story_id': story.id,
                'load_case_id': load_case.id,
                'direction': drift_obj.direction,
                'absolute_max_drift': absolute_max_drift,
                'sign': sign,
                'original_max': max_val,
                'original_min': min_val,
            })
        
        # Bulk insert
        if drift_records:
            abs_maxmin_repo.bulk_create(drift_records)
            self._report_progress(f"Calculated absolute max/min for {len(drift_records)} drift records", 0, 1)
