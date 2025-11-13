"""Import service for RPS projects."""

from typing import Optional, Callable
from pathlib import Path
from dataclasses import dataclass
import pandas as pd
import json
from datetime import datetime

from services.project_service import ProjectContext, ensure_project_context
from database.models import ResultSet, LoadCase, Story, Element
from database.repository import (
    ProjectRepository, ResultSetRepository, LoadCaseRepository,
    StoryRepository, ElementRepository, CacheRepository, ElementCacheRepository
)


@dataclass
class ImportProjectExcelOptions:
    """Options for importing Excel project."""
    excel_path: Path
    new_project_name: Optional[str] = None  # If None, use name from Excel
    overwrite_existing: bool = False


@dataclass
class ImportPreview:
    """Preview of project to be imported."""
    project_name: str
    description: str
    created_at: str
    exported_at: str
    result_sets_count: int
    load_cases_count: int
    stories_count: int
    elements_count: int
    result_types: list
    warnings: list
    can_import: bool


class ImportService:
    """Service for importing Excel project files."""

    def preview_import(self, excel_path: Path) -> ImportPreview:
        """Preview Excel file before importing.

        Validates file structure and returns summary without creating project.

        Args:
            excel_path: Path to .xlsx file

        Returns:
            ImportPreview with project summary and validation status
        """
        warnings = []
        can_import = True

        try:
            # Read IMPORT_DATA sheet (may be split across multiple rows)
            import_data_df = pd.read_excel(excel_path, sheet_name="IMPORT_DATA")

            # Concatenate all rows to reassemble the JSON
            json_chunks = import_data_df['import_metadata'].tolist()
            json_str = ''.join(str(chunk) for chunk in json_chunks if pd.notna(chunk))

            import_metadata = json.loads(json_str)

            project_info = import_metadata.get('project', {})
            result_sheets = import_metadata.get('result_sheet_mapping', {})

            print(f"DEBUG PREVIEW: result_sheet_mapping = {result_sheets}")

            # Validate required sheets exist
            xl_file = pd.ExcelFile(excel_path)
            print(f"DEBUG PREVIEW: Actual Excel sheets = {xl_file.sheet_names}")
            required_sheets = ["README", "Result Sets", "Load Cases", "Stories", "IMPORT_DATA"]
            missing_sheets = [s for s in required_sheets if s not in xl_file.sheet_names]

            if missing_sheets:
                warnings.append(f"Missing required sheets: {', '.join(missing_sheets)}")
                can_import = False

            # Validate result data sheets exist
            all_result_types = result_sheets.get('global', []) + result_sheets.get('element', [])
            missing_data = [rt for rt in all_result_types if rt[:31] not in xl_file.sheet_names]

            if missing_data:
                warnings.append(f"Missing result data sheets: {', '.join(missing_data)}")

            return ImportPreview(
                project_name=project_info.get('name', 'Unknown'),
                description=project_info.get('description', ''),
                created_at=project_info.get('created_at', ''),
                exported_at=import_metadata.get('export_timestamp', ''),
                result_sets_count=len(import_metadata.get('result_sets', [])),
                load_cases_count=len(import_metadata.get('load_cases', [])),
                stories_count=len(import_metadata.get('stories', [])),
                elements_count=len(import_metadata.get('elements', [])),
                result_types=all_result_types,
                warnings=warnings,
                can_import=can_import
            )

        except Exception as e:
            return ImportPreview(
                project_name="Error",
                description="",
                created_at="",
                exported_at="",
                result_sets_count=0,
                load_cases_count=0,
                stories_count=0,
                elements_count=0,
                result_types=[],
                warnings=[f"Failed to read Excel file: {str(e)}"],
                can_import=False
            )

    def import_project_excel(
        self,
        options: ImportProjectExcelOptions,
        progress_callback: Optional[Callable[[str, int, int], None]] = None
    ) -> ProjectContext:
        """Import project from Excel workbook.

        Args:
            options: Import options
            progress_callback: Optional callback(message, current, total)

        Returns:
            ProjectContext for newly imported project

        Raises:
            ValueError: If Excel file is invalid
            IOError: If file cannot be read
        """
        total_steps = 8

        # Step 1: Read import metadata
        if progress_callback:
            progress_callback("Reading import metadata...", 1, total_steps)

        import_data_df = pd.read_excel(options.excel_path, sheet_name="IMPORT_DATA")

        # Concatenate all rows to reassemble the JSON (may be chunked)
        json_chunks = import_data_df['import_metadata'].tolist()
        json_str = ''.join(str(chunk) for chunk in json_chunks if pd.notna(chunk))

        import_metadata = json.loads(json_str)

        project_info = import_metadata.get('project', {})
        project_name = options.new_project_name or project_info.get('name')

        # Step 2: Create project
        if progress_callback:
            progress_callback("Creating project...", 2, total_steps)

        # Create project context (name is already validated by UI)
        context = ensure_project_context(
            name=project_name,
            description=project_info.get('description', '')
        )

        # Step 3: Import metadata (result sets, load cases, stories, elements)
        if progress_callback:
            progress_callback("Importing metadata...", 3, total_steps)

        self._import_metadata(context, import_metadata)

        # Step 4-7: Import complete database from IMPORT_DATA
        if progress_callback:
            progress_callback("Importing database...", 4, total_steps)

        self._import_database_from_json(
            context, import_metadata,
            lambda msg, curr, tot: progress_callback(msg, 4 + curr, total_steps) if progress_callback else None
        )

        # Step 8: Complete
        if progress_callback:
            progress_callback("Import complete!", total_steps, total_steps)

        return context

    def _import_metadata(self, context: ProjectContext, import_metadata: dict) -> None:
        """Import metadata tables (result sets, load cases, stories, elements).

        Args:
            context: Project context
            import_metadata: Parsed IMPORT_DATA JSON
        """
        with context.session() as session:
            project_repo = ProjectRepository(session)
            project = project_repo.get_by_name(context.name)

            if not project:
                raise ValueError(f"Project '{context.name}' not found in database")

            # Import result sets
            result_set_repo = ResultSetRepository(session)
            result_set_mapping = {}
            print(f"DEBUG: Importing {len(import_metadata.get('result_sets', []))} result sets")
            for rs_data in import_metadata.get('result_sets', []):
                print(f"DEBUG: Creating result set: {rs_data['name']}")
                rs = result_set_repo.create(
                    project_id=project.id,
                    name=rs_data['name'],
                    description=rs_data.get('description', '')
                )
                result_set_mapping[rs_data['name']] = rs.id

            # Import result categories
            from database.repository import ResultCategoryRepository
            result_category_repo = ResultCategoryRepository(session)
            result_category_mapping = {}
            for rc_data in import_metadata.get('result_categories', []):
                result_set_id = result_set_mapping.get(rc_data.get('result_set_name'))
                if result_set_id:
                    rc = result_category_repo.create(
                        result_set_id=result_set_id,
                        category_name=rc_data['category_name'],
                        category_type=rc_data.get('category_type', 'Global')
                    )
                    # Use composite key: (result_set_name, category_name) -> category_id
                    key = (rc_data.get('result_set_name'), rc_data['category_name'])
                    result_category_mapping[key] = rc.id

            # Import load cases
            load_case_repo = LoadCaseRepository(session)
            load_case_mapping = {}
            for lc_data in import_metadata.get('load_cases', []):
                lc = load_case_repo.create(
                    project_id=project.id,
                    name=lc_data['name'],
                    description=lc_data.get('description', '')
                )
                load_case_mapping[lc_data['name']] = lc.id

            # Import stories
            story_repo = StoryRepository(session)
            story_mapping = {}
            for s_data in import_metadata.get('stories', []):
                s = story_repo.create(
                    project_id=project.id,
                    name=s_data['name'],
                    sort_order=s_data.get('sort_order', 0),
                    elevation=s_data.get('elevation', 0.0)
                )
                story_mapping[s_data['name']] = s.id

            # Import elements
            element_repo = ElementRepository(session)
            element_mapping = {}
            for e_data in import_metadata.get('elements', []):
                e = element_repo.create(
                    project_id=project.id,
                    name=e_data['name'],
                    element_type=e_data.get('element_type', 'Wall'),
                    unique_name=e_data.get('unique_name', '')
                )
                element_mapping[e_data['name']] = e.id

            session.commit()

            # Store mappings for result data import
            self._import_context = {
                'project_id': project.id,
                'result_set_mapping': result_set_mapping,
                'result_category_mapping': result_category_mapping,
                'load_case_mapping': load_case_mapping,
                'story_mapping': story_mapping,
                'element_mapping': element_mapping,
            }

    def _import_database_from_json(
        self,
        context: ProjectContext,
        import_metadata: dict,
        progress_callback: Optional[Callable] = None
    ) -> None:
        """Import complete per-project database from JSON in IMPORT_DATA sheet."""
        from database.models import (
            StoryDrift, StoryAcceleration, StoryForce, StoryDisplacement,
            AbsoluteMaxMinDrift, QuadRotation, WallShear,
            GlobalResultsCache, ElementResultsCache
        )

        normalized_data = import_metadata.get('normalized_data', {})
        cache_data = import_metadata.get('cache_data', {})

        with context.session() as session:
            # Get mappings
            story_mapping = self._import_context['story_mapping']
            load_case_mapping = self._import_context['load_case_mapping']
            result_set_mapping = self._import_context['result_set_mapping']
            result_category_mapping = self._import_context['result_category_mapping']
            element_mapping = self._import_context['element_mapping']
            project_id = self._import_context['project_id']

            # Import normalized tables
            if progress_callback:
                progress_callback("Importing story drifts...", 0, 9)

            drift_records = normalized_data.get('story_drifts', [])
            print(f"DEBUG: Found {len(drift_records)} story_drifts records in JSON")
            drift_count = 0

            for drift_data in drift_records:
                story_id = story_mapping.get(drift_data['story_name'])
                load_case_id = load_case_mapping.get(drift_data['load_case_name'])
                if story_id and load_case_id:
                    entry = StoryDrift(
                        story_id=story_id,
                        load_case_id=load_case_id,
                        direction=drift_data['direction'],
                        drift=drift_data['drift'],
                        max_drift=drift_data.get('max_drift'),
                        min_drift=drift_data.get('min_drift'),
                        story_sort_order=drift_data.get('story_sort_order', 0)
                    )
                    session.add(entry)
                    drift_count += 1

            print(f"DEBUG: Imported {drift_count} story_drifts records")

            if progress_callback:
                progress_callback("Importing story accelerations...", 1, 9)

            accel_records = normalized_data.get('story_accelerations', [])
            print(f"DEBUG: Found {len(accel_records)} story_accelerations records in JSON")
            accel_count = 0

            for accel_data in accel_records:
                story_id = story_mapping.get(accel_data['story_name'])
                load_case_id = load_case_mapping.get(accel_data['load_case_name'])
                # Get result_category_id from mapping
                result_set_name = accel_data.get('result_set_name')  # Will add to export
                result_category_name = accel_data.get('result_category_name')
                result_category_id = None
                if result_set_name and result_category_name:
                    result_category_id = result_category_mapping.get((result_set_name, result_category_name))

                if story_id and load_case_id:
                    entry = StoryAcceleration(
                        story_id=story_id,
                        load_case_id=load_case_id,
                        result_category_id=result_category_id,
                        direction=accel_data['direction'],
                        acceleration=accel_data['acceleration'],
                        max_acceleration=accel_data.get('max_acceleration'),
                        min_acceleration=accel_data.get('min_acceleration'),
                        story_sort_order=accel_data.get('story_sort_order', 0)
                    )
                    session.add(entry)
                    accel_count += 1
                else:
                    if not story_id:
                        print(f"DEBUG: Missing story_id for {accel_data.get('story_name')}")
                    if not load_case_id:
                        print(f"DEBUG: Missing load_case_id for {accel_data.get('load_case_name')}")

            print(f"DEBUG: Imported {accel_count} story_accelerations records")

            if progress_callback:
                progress_callback("Importing story forces...", 2, 6)

            force_records = normalized_data.get('story_forces', [])
            print(f"DEBUG: Found {len(force_records)} story_forces records in JSON")
            force_count = 0

            for force_data in force_records:
                story_id = story_mapping.get(force_data['story_name'])
                load_case_id = load_case_mapping.get(force_data['load_case_name'])
                # Get result_category_id from mapping
                result_set_name = force_data.get('result_set_name')
                result_category_name = force_data.get('result_category_name')
                result_category_id = None
                if result_set_name and result_category_name:
                    result_category_id = result_category_mapping.get((result_set_name, result_category_name))

                if story_id and load_case_id:
                    entry = StoryForce(
                        story_id=story_id,
                        load_case_id=load_case_id,
                        result_category_id=result_category_id,
                        direction=force_data['direction'],
                        location=force_data.get('location'),
                        force=force_data['force'],
                        max_force=force_data.get('max_force'),
                        min_force=force_data.get('min_force'),
                        story_sort_order=force_data.get('story_sort_order', 0)
                    )
                    session.add(entry)
                    force_count += 1

            print(f"DEBUG: Imported {force_count} story_forces records")

            if progress_callback:
                progress_callback("Importing story displacements...", 3, 6)

            disp_records = normalized_data.get('story_displacements', [])
            print(f"DEBUG: Found {len(disp_records)} story_displacements records in JSON")
            disp_count = 0

            for disp_data in disp_records:
                story_id = story_mapping.get(disp_data['story_name'])
                load_case_id = load_case_mapping.get(disp_data['load_case_name'])
                # Get result_category_id from mapping
                result_set_name = disp_data.get('result_set_name')
                result_category_name = disp_data.get('result_category_name')
                result_category_id = None
                if result_set_name and result_category_name:
                    result_category_id = result_category_mapping.get((result_set_name, result_category_name))

                if story_id and load_case_id:
                    entry = StoryDisplacement(
                        story_id=story_id,
                        load_case_id=load_case_id,
                        result_category_id=result_category_id,
                        direction=disp_data['direction'],
                        displacement=disp_data['displacement'],
                        max_displacement=disp_data.get('max_displacement'),
                        min_displacement=disp_data.get('min_displacement'),
                        story_sort_order=disp_data.get('story_sort_order', 0)
                    )
                    session.add(entry)
                    disp_count += 1

            print(f"DEBUG: Imported {disp_count} story_displacements records")

            # Import absolute max/min drifts
            if progress_callback:
                progress_callback("Importing max/min drifts...", 4, 9)

            maxmin_records = normalized_data.get('absolute_maxmin_drifts', [])
            print(f"DEBUG: Found {len(maxmin_records)} absolute_maxmin_drifts records in JSON")
            imported_count = 0

            for maxmin_data in maxmin_records:
                result_set_id = result_set_mapping.get(maxmin_data['result_set_name'])
                story_id = story_mapping.get(maxmin_data['story_name'])
                load_case_id = load_case_mapping.get(maxmin_data['load_case_name'])
                if result_set_id and story_id and load_case_id:
                    entry = AbsoluteMaxMinDrift(
                        project_id=project_id,
                        result_set_id=result_set_id,
                        story_id=story_id,
                        load_case_id=load_case_id,
                        direction=maxmin_data['direction'],
                        absolute_max_drift=maxmin_data['absolute_max_drift'],
                        sign=maxmin_data['sign'],
                        original_max=maxmin_data.get('original_max'),
                        original_min=maxmin_data.get('original_min')
                        # Note: story_sort_order not in this table, order comes from Story.sort_order
                    )
                    session.add(entry)
                    imported_count += 1

            print(f"DEBUG: Imported {imported_count} absolute_maxmin_drifts records")

            # Import quad rotations
            if progress_callback:
                progress_callback("Importing quad rotations...", 5, 9)

            quad_records = normalized_data.get('quad_rotations', [])
            print(f"DEBUG: Found {len(quad_records)} quad_rotations records in JSON")
            quad_count = 0

            for quad_data in quad_records:
                element_id = element_mapping.get(quad_data['element_name'])
                story_id = story_mapping.get(quad_data['story_name'])
                load_case_id = load_case_mapping.get(quad_data['load_case_name'])
                if element_id and story_id and load_case_id:
                    entry = QuadRotation(
                        element_id=element_id,
                        story_id=story_id,
                        load_case_id=load_case_id,
                        rotation=quad_data['rotation'],
                        max_rotation=quad_data.get('max_rotation'),
                        min_rotation=quad_data.get('min_rotation'),
                        story_sort_order=quad_data.get('story_sort_order', 0)
                    )
                    session.add(entry)
                    quad_count += 1

            print(f"DEBUG: Imported {quad_count} quad_rotations records")

            # Import wall shears
            if progress_callback:
                progress_callback("Importing wall shears...", 6, 9)

            wall_records = normalized_data.get('wall_shears', [])
            print(f"DEBUG: Found {len(wall_records)} wall_shears records in JSON")
            wall_count = 0

            for wall_data in wall_records:
                element_id = element_mapping.get(wall_data['element_name'])
                story_id = story_mapping.get(wall_data['story_name'])
                load_case_id = load_case_mapping.get(wall_data['load_case_name'])
                if element_id and story_id and load_case_id:
                    entry = WallShear(
                        element_id=element_id,
                        story_id=story_id,
                        load_case_id=load_case_id,
                        direction=wall_data['direction'],
                        location=wall_data.get('location'),
                        force=wall_data['force'],
                        max_force=wall_data.get('max_force'),
                        min_force=wall_data.get('min_force'),
                        story_sort_order=wall_data.get('story_sort_order', 0)
                    )
                    session.add(entry)
                    wall_count += 1

            print(f"DEBUG: Imported {wall_count} wall_shears records")

            # Import cache tables
            if progress_callback:
                progress_callback("Importing global cache...", 7, 9)

            global_cache_records = cache_data.get('global_results_cache', [])
            print(f"DEBUG: Found {len(global_cache_records)} global_results_cache records in JSON")
            global_cache_count = 0

            for cache_data_row in global_cache_records:
                result_set_id = result_set_mapping.get(cache_data_row['result_set_name'])
                story_id = story_mapping.get(cache_data_row['story_name'])
                if result_set_id and story_id:
                    entry = GlobalResultsCache(
                        project_id=project_id,
                        result_set_id=result_set_id,
                        story_id=story_id,
                        result_type=cache_data_row['result_type'],
                        story_sort_order=cache_data_row.get('story_sort_order', 0),
                        results_matrix=cache_data_row['results_matrix']
                    )
                    session.add(entry)
                    global_cache_count += 1

            print(f"DEBUG: Imported {global_cache_count} global_results_cache records")

            if progress_callback:
                progress_callback("Importing element cache...", 8, 9)

            element_cache_records = cache_data.get('element_results_cache', [])
            print(f"DEBUG: Found {len(element_cache_records)} element_results_cache records in JSON")
            element_cache_count = 0

            for cache_data_row in element_cache_records:
                result_set_id = result_set_mapping.get(cache_data_row['result_set_name'])
                element_id = element_mapping.get(cache_data_row['element_name'])
                story_id = story_mapping.get(cache_data_row['story_name'])
                if result_set_id and element_id and story_id:
                    entry = ElementResultsCache(
                        project_id=project_id,
                        result_set_id=result_set_id,
                        element_id=element_id,
                        story_id=story_id,
                        result_type=cache_data_row['result_type'],
                        story_sort_order=cache_data_row.get('story_sort_order', 0),
                        results_matrix=cache_data_row['results_matrix']
                    )
                    session.add(entry)
                    element_cache_count += 1

            print(f"DEBUG: Imported {element_cache_count} element_results_cache records")

            session.commit()
            print(f"DEBUG: Database import complete!")

    def _import_result_data(
        self,
        context: ProjectContext,
        excel_path: Path,
        import_metadata: dict,
        progress_callback: Optional[Callable] = None
    ) -> None:
        """Import result data from Excel sheets into cache tables.

        Args:
            context: Project context
            excel_path: Path to Excel file
            import_metadata: Parsed IMPORT_DATA JSON
            progress_callback: Optional progress callback
        """
        from database.models import GlobalResultsCache, ElementResultsCache

        result_sheets = import_metadata.get('result_sheet_mapping', {})
        global_types = result_sheets.get('global', [])
        element_types = result_sheets.get('element', [])

        print(f"DEBUG: Importing result data")
        print(f"DEBUG: Global types: {global_types}")
        print(f"DEBUG: Element types: {element_types}")

        total = len(global_types) + len(element_types)
        current = 0

        with context.session() as session:
            cache_repo = CacheRepository(session)
            element_cache_repo = ElementCacheRepository(session)

            # Import global results
            for result_type in global_types:
                if progress_callback:
                    progress_callback(f"Importing {result_type}...", current, total)

                sheet_name = result_type[:31]
                print(f"DEBUG: Reading sheet '{sheet_name}' for {result_type}")
                df = pd.read_excel(excel_path, sheet_name=sheet_name)
                print(f"DEBUG: Sheet has {len(df)} rows, {len(df.columns)} columns")

                # Parse DataFrame and write to GlobalResultsCache
                self._import_global_result(session, cache_repo, result_type, df)
                current += 1

            # Import element results
            for result_type in element_types:
                if progress_callback:
                    progress_callback(f"Importing {result_type}...", current, total)

                sheet_name = result_type[:31]
                print(f"DEBUG: Reading sheet '{sheet_name}' for {result_type}")
                df = pd.read_excel(excel_path, sheet_name=sheet_name)
                print(f"DEBUG: Sheet has {len(df)} rows, {len(df.columns)} columns")

                # Parse DataFrame and write to ElementResultsCache
                self._import_element_result(session, element_cache_repo, result_type, df)
                current += 1

            print(f"DEBUG: Committing session...")
            session.commit()
            print(f"DEBUG: Import complete!")

    def _import_global_result(self, session, cache_repo, result_type: str, df: pd.DataFrame) -> None:
        """Import global result data into GlobalResultsCache.

        Args:
            session: SQLAlchemy session
            cache_repo: CacheRepository instance
            result_type: Result type name (e.g., "Drifts_X")
            df: DataFrame with result data
        """
        from database.models import GlobalResultsCache
        from config.result_config import RESULT_CONFIGS

        # Assume first result set (can be enhanced for multi-result-set)
        result_set_id = list(self._import_context['result_set_mapping'].values())[0]
        story_mapping = self._import_context['story_mapping']
        project_id = self._import_context['project_id']

        # Extract base type (e.g., "Drifts_X" -> "Drifts")
        config = RESULT_CONFIGS.get(result_type)
        if not config:
            print(f"Warning: Unknown result type {result_type}, skipping")
            return

        base_type = result_type.split('_')[0] if '_' in result_type else result_type
        # Extract direction from result_type (e.g., "Drifts_X" -> "X", "Accelerations_UX" -> "UX")
        direction = result_type.split('_')[1] if '_' in result_type else None

        print(f"DEBUG: Importing {result_type} -> base_type: {base_type}, direction: {direction}")
        print(f"DEBUG: Story mapping has {len(story_mapping)} stories")

        # Get load case mapping once
        load_case_mapping = self._import_context['load_case_mapping']

        entries_added = 0
        normalized_total = 0
        # Process each story row
        for idx, row in df.iterrows():
            story_name = row['Story']
            story_id = story_mapping.get(story_name)

            if not story_id:
                print(f"DEBUG: Story '{story_name}' not found in mapping, skipping")
                continue

            # Build results_matrix (load case columns)
            results_matrix = {}
            for col in df.columns:
                if col != 'Story':
                    results_matrix[col] = float(row[col]) if pd.notna(row[col]) else None

            # Create cache entry
            cache_entry = GlobalResultsCache(
                project_id=project_id,
                result_set_id=result_set_id,
                story_id=story_id,
                result_type=base_type,
                story_sort_order=idx,  # Use Excel row order
                results_matrix=results_matrix
            )
            session.add(cache_entry)
            entries_added += 1

            # ALSO write to normalized tables for each load case
            for load_case_name, value in results_matrix.items():
                load_case_id = load_case_mapping.get(load_case_name)
                if not load_case_id or value is None:
                    continue

                # Create normalized result entry based on result type
                try:
                    self._create_normalized_result(session, base_type, direction, project_id, result_set_id,
                                                   story_id, load_case_id, value, story_sort_order=idx)
                    normalized_total += 1
                except Exception as e:
                    print(f"DEBUG: Error creating normalized result: {e}")

        print(f"DEBUG: Added {entries_added} cache entries and {normalized_total} normalized entries for {result_type}")

    def _create_normalized_result(self, session, result_type: str, direction: str, project_id: int,
                                   result_set_id: int, story_id: int, load_case_id: int, value: float,
                                   story_sort_order: int = 0):
        """Create normalized result entry in the appropriate table."""
        from database.models import StoryDrift, StoryAcceleration, StoryForce, StoryDisplacement

        if not direction:
            print(f"DEBUG: No direction provided for {result_type}, skipping normalized table creation")
            return

        if result_type == 'Drifts':
            entry = StoryDrift(
                story_id=story_id,
                load_case_id=load_case_id,
                direction=direction,  # Use extracted direction (X or Y)
                drift=value,
                story_sort_order=story_sort_order
            )
            session.add(entry)
        elif result_type == 'Accelerations':
            entry = StoryAcceleration(
                story_id=story_id,
                load_case_id=load_case_id,
                direction=direction,  # Use extracted direction (UX or UY)
                acceleration=value,
                story_sort_order=story_sort_order
            )
            session.add(entry)
        elif result_type == 'Forces':
            entry = StoryForce(
                story_id=story_id,
                load_case_id=load_case_id,
                direction=direction,  # Use extracted direction (VX or VY)
                force=value,
                story_sort_order=story_sort_order
            )
            session.add(entry)
        elif result_type == 'Displacements':
            entry = StoryDisplacement(
                story_id=story_id,
                load_case_id=load_case_id,
                direction=direction,  # Use extracted direction (UX, UY, or UZ)
                displacement=value,
                story_sort_order=story_sort_order
            )
            session.add(entry)

    def _import_element_result(self, session, element_cache_repo, result_type: str, df: pd.DataFrame) -> None:
        """Import element result data into ElementResultsCache.

        Args:
            session: SQLAlchemy session
            element_cache_repo: ElementCacheRepository instance
            result_type: Result type name (e.g., "WallShears_V2")
            df: DataFrame with element result data
        """
        from database.models import ElementResultsCache

        result_set_id = list(self._import_context['result_set_mapping'].values())[0]
        story_mapping = self._import_context['story_mapping']
        element_mapping = self._import_context['element_mapping']
        project_id = self._import_context['project_id']

        # Process each element row
        for idx, row in df.iterrows():
            element_name = row['Element']
            story_name = row['Story']

            element_id = element_mapping.get(element_name)
            story_id = story_mapping.get(story_name)

            if not element_id or not story_id:
                continue

            # Build results_matrix
            results_matrix = {}
            for col in df.columns:
                if col not in ['Element', 'Story']:
                    results_matrix[col] = float(row[col]) if pd.notna(row[col]) else None

            # Create cache entry
            cache_entry = ElementResultsCache(
                project_id=project_id,
                result_set_id=result_set_id,
                element_id=element_id,
                story_id=story_id,
                result_type=result_type,
                story_sort_order=idx,
                results_matrix=results_matrix
            )
            session.add(cache_entry)
