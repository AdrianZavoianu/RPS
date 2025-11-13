Now I want to move to implement the export features. The export at the project level will have 2 main option export project and export data. Export project will export everything needed to re-inport the current project on another device. Th export data will save all the results in individual tables similar with the output for the @Old_scripts. Also combine all into one file should be possible. Options for the export files type shall be excel and csv. Lets plan the implementation of this

 Overview

   Implement two export features with Excel/CSV support:
   1. Export Project - Complete project package (.rpsproj zip) for re-import on another device
   2. Export Data - Result tables matching Old_scripts format with Excel multi-sheet combine option

   Key Clarifications

   ✅ Combined export: Excel multi-sheet workbooks only (not CSV)
   ✅ CSV export: Always one-table-per-file (no combining)
   ✅ Data scope: Only display data (what UI shows), no raw ETABS metadata
   ✅ Project export: SQLite DB + manifest.json for future import wizard
   ✅ Import feature: Will be added to Projects window (Main window)
   ✅ Old scripts format: One file per result type/direction with all load cases as columns

   ---
   Phase 1: Requirements & UX Design

   1.1 Export Modes Specification

   Mode 1: Export Project
   - Purpose: Complete project backup for re-import on another device
   - Output: .rpsproj file (renamed zip archive)
   - Contents:
     - SQLite database file ({slug}.db)
     - manifest.json with metadata:
     {
     "project_name": "160Wil",
     "slug": "160wil",
     "description": "Project description",
     "created_at": "2024-11-08T10:30:00Z",
     "exported_at": "2024-11-08T15:45:00Z",
     "app_version": "2.0",
     "db_filename": "160wil.db",
     "db_checksum_sha256": "abc123...",
     "catalog_metadata": {
       "result_set_count": 3,
       "load_case_count": 120,
       "story_count": 8,
       "last_opened": "2024-11-07T09:00:00Z"
     }
   }
   - Re-import process (future):
     a. User selects .rpsproj file in Projects window
     b. Extract manifest, validate checksum
     c. Create catalog entry from manifest metadata
     d. Extract DB to data/projects/{slug}/{slug}.db
     e. Refresh project list

   Mode 2: Export Data
   - Purpose: Export result tables for analysis/reporting (matching Old_scripts)
   - Output formats:
     - Excel per-table: One .xlsx file per result type/direction
         - Example: Drifts_X.xlsx (Story | TH01 | TH02 | MCR1 | ...)
     - Excel combined: One .xlsx workbook with multiple sheets
         - Example: 160Wil_Results.xlsx with sheets: Drifts_X, Drifts_Y, Accelerations_UX, ...
     - CSV per-table: One .csv file per result type/direction (no combining)
   - Data included: Only what's needed for display (no raw import metadata)
   - Scope options:
     - Current view only (single result type/direction)
     - All result types for current result set
     - Multiple result sets (user selects)

   1.2 File Naming Conventions

   Project Export:
   - Format: {ProjectName}_{YYYYMMDD_HHMMSS}.rpsproj
   - Example: 160Wil_20241108_154530.rpsproj

   Data Export (per-table):
   - Standard: {ResultType}_{Direction}.{ext}
     - Examples: Drifts_X.xlsx, WallShears_V2.csv
   - Max/Min: {ResultType}_{Direction}_Max.{ext} and {ResultType}_{Direction}_Min.{ext}
     - Examples: Drifts_X_Max.xlsx, Drifts_X_Min.xlsx
   - Directionless: {ResultType}.{ext}
     - Examples: QuadRotations.xlsx, MinAxial.csv

   Data Export (combined):
   - Format: {ProjectName}_{ResultSetName}_{YYYYMMDD_HHMMSS}.xlsx
   - Example: 160Wil_DES_20241108_154530.xlsx
   - Sheets named: Drifts_X, Drifts_Y, Accelerations_UX, etc.

   1.3 Deliverable

    Create: docs/implementation/EXPORT_SPECIFICATION.md (~50 lines)
   - Document both export modes with examples
   - File format specifications
   - Re-import workflow (high-level, for future implementation)
   - Wireframe mockups for export dialogs

   ---
   Phase 2: Export Domain Models & Service Layer

   2.1 Export Service Structure

   File: src/services/export_service.py (~400 lines)

   from dataclasses import dataclass
   from typing import Optional, List, Callable
   from pathlib import Path
   import json
   import hashlib
   import zipfile
   import pandas as pd
   from datetime import datetime

   @dataclass
   class ProjectExportOptions:
       """Options for project export."""
       output_path: Path  # Path to .rpsproj file
       include_metadata: bool = True  # Include manifest.json
       compress_level: int = 9  # ZIP compression (0-9)

   @dataclass
   class DataExportOptions:
       """Options for data export."""
       result_set_ids: List[int]  # Result sets to export
       result_types: List[str]  # Result types to export (e.g., ["Drifts", "Accelerations"])
       include_directions: List[str]  # Directions (e.g., ["X", "Y", "V2", "V3"])
       include_maxmin: bool = True  # Export Max/Min envelopes
       format: str = "excel"  # "excel" or "csv"
       combine_mode: str = "per_table"  # "per_table" or "combined" (Excel only)
       output_folder: Optional[Path] = None  # For per-table exports
       output_file: Optional[Path] = None  # For combined exports

   @dataclass
   class ExportManifest:
       """Manifest metadata for project export."""
       project_name: str
       slug: str
       description: str
       created_at: datetime
       exported_at: datetime
       app_version: str
       db_filename: str
       db_checksum_sha256: str
       catalog_metadata: dict

       def to_json(self) -> str:
           """Serialize to JSON."""
           return json.dumps({
               "project_name": self.project_name,
               "slug": self.slug,
               "description": self.description,
               "created_at": self.created_at.isoformat(),
               "exported_at": self.exported_at.isoformat(),
               "app_version": self.app_version,
               "db_filename": self.db_filename,
               "db_checksum_sha256": self.db_checksum_sha256,
               "catalog_metadata": self.catalog_metadata,
           }, indent=2)

   class ExportService:
       """Service for exporting projects and result data."""

       APP_VERSION = "2.0"  # RPS version

       def __init__(self, project_context, result_service):
           self.project_context = project_context
           self.result_service = result_service
           self.catalog_repo = CatalogRepository()

       # ===== PROJECT EXPORT =====

       def export_project(self, options: ProjectExportOptions,
                         progress_callback: Optional[Callable] = None) -> None:
           """Export complete project as .rpsproj bundle."""
           # 1. Build manifest
           manifest = self._build_manifest()

           # 2. Create zip archive
           with zipfile.ZipFile(options.output_path, 'w', zipfile.ZIP_DEFLATED) as zf:
               # Add manifest.json
               zf.writestr("manifest.json", manifest.to_json())

               # Add database file
               db_path = self.project_context.db_path
               zf.write(db_path, f"{manifest.slug}.db")

               if progress_callback:
                   progress_callback("Export complete", 1, 1)

       def _build_manifest(self) -> ExportManifest:
           """Build export manifest from project data."""
           catalog_project = self.catalog_repo.get_by_slug(self.project_context.slug)

           # Calculate DB checksum
           db_checksum = self._calculate_file_checksum(self.project_context.db_path)

           # Gather catalog metadata
           with self.project_context.session_scope() as session:
               result_sets = session.query(ResultSet).count()
               load_cases = session.query(LoadCase).count()
               stories = session.query(Story).count()

           return ExportManifest(
               project_name=catalog_project.name,
               slug=catalog_project.slug,
               description=catalog_project.description or "",
               created_at=catalog_project.created_at,
               exported_at=datetime.now(),
               app_version=self.APP_VERSION,
               db_filename=f"{catalog_project.slug}.db",
               db_checksum_sha256=db_checksum,
               catalog_metadata={
                   "result_set_count": result_sets,
                   "load_case_count": load_cases,
                   "story_count": stories,
                   "last_opened": catalog_project.last_opened.isoformat() if catalog_project.last_opened else None,
               }
           )

       def _calculate_file_checksum(self, file_path: Path) -> str:
           """Calculate SHA256 checksum of file."""
           sha256 = hashlib.sha256()
           with open(file_path, 'rb') as f:
               for chunk in iter(lambda: f.read(8192), b''):
                   sha256.update(chunk)
           return sha256.hexdigest()

       # ===== DATA EXPORT =====

       def export_data(self, options: DataExportOptions,
                      progress_callback: Optional[Callable] = None) -> None:
           """Export result data based on options."""
           if options.format == "excel" and options.combine_mode == "combined":
               self._export_combined_excel(options, progress_callback)
           else:
               self._export_per_table(options, progress_callback)

       def _export_combined_excel(self, options: DataExportOptions,
                                  progress_callback: Optional[Callable] = None) -> None:
           """Export all results to single multi-sheet Excel workbook."""
           with pd.ExcelWriter(options.output_file, engine='openpyxl') as writer:
               total_exports = len(options.result_types) * len(options.include_directions)
               current = 0

               for result_set_id in options.result_set_ids:
                   for result_type in options.result_types:
                       for direction in options.include_directions:
                           # Get dataset
                           dataset = self.result_service.get_standard_dataset(
                               result_type, direction, result_set_id
                           )

                           # Write to sheet
                           sheet_name = f"{result_type}_{direction}"
                           dataset.df.to_excel(writer, sheet_name=sheet_name, index=False)

                           # Update progress
                           current += 1
                           if progress_callback:
                               progress_callback(f"Exporting {sheet_name}", current, total_exports)

                           # Export Max/Min if requested
                           if options.include_maxmin:
                               maxmin = self.result_service.get_maxmin_dataset(
                                   result_type, direction, result_set_id
                               )
                               if maxmin.max_df is not None:
                                   maxmin.max_df.to_excel(writer, sheet_name=f"{sheet_name}_Max", index=False)
                               if maxmin.min_df is not None:
                                   maxmin.min_df.to_excel(writer, sheet_name=f"{sheet_name}_Min", index=False)

       def _export_per_table(self, options: DataExportOptions,
                            progress_callback: Optional[Callable] = None) -> None:
           """Export each result type/direction to separate file."""
           options.output_folder.mkdir(parents=True, exist_ok=True)

           total_exports = len(options.result_types) * len(options.include_directions)
           current = 0

           for result_set_id in options.result_set_ids:
               for result_type in options.result_types:
                   for direction in options.include_directions:
                       # Build filename
                       filename = self._build_filename(result_type, direction, options.format)
                       file_path = options.output_folder / filename

                       # Get dataset
                       dataset = self.result_service.get_standard_dataset(
                           result_type, direction, result_set_id
                       )

                       # Write file
                       if options.format == "excel":
                           dataset.df.to_excel(file_path, index=False)
                       else:  # csv
                           dataset.df.to_csv(file_path, index=False)

                       # Update progress
                       current += 1
                       if progress_callback:
                           progress_callback(f"Exported {filename}", current, total_exports)

                       # Export Max/Min if requested
                       if options.include_maxmin:
                           self._export_maxmin_files(result_type, direction, result_set_id,
                                                    options.output_folder, options.format)

       def _export_maxmin_files(self, result_type: str, direction: str,
                               result_set_id: int, output_folder: Path, format: str) -> None:
           """Export Max and Min envelope files."""
           maxmin = self.result_service.get_maxmin_dataset(result_type, direction, result_set_id)

           if maxmin.max_df is not None:
               filename = self._build_filename(result_type, direction, format, envelope="Max")
               file_path = output_folder / filename
               if format == "excel":
                   maxmin.max_df.to_excel(file_path, index=False)
               else:
                   maxmin.max_df.to_csv(file_path, index=False)

           if maxmin.min_df is not None:
               filename = self._build_filename(result_type, direction, format, envelope="Min")
               file_path = output_folder / filename
               if format == "excel":
                   maxmin.min_df.to_excel(file_path, index=False)
               else:
                   maxmin.min_df.to_csv(file_path, index=False)

       def _build_filename(self, result_type: str, direction: str,
                          format: str, envelope: Optional[str] = None) -> str:
           """Build filename matching Old_scripts convention."""
           ext = "xlsx" if format == "excel" else "csv"

           # Handle directionless results
           if not direction:
               base = result_type
           else:
               base = f"{result_type}_{direction}"

           if envelope:
               base = f"{base}_{envelope}"

           return f"{base}.{ext}"

   2.2 Unit Tests

   File: tests/services/test_export_service.py (~200 lines)

   import pytest
   from pathlib import Path
   from services.export_service import ExportService, ProjectExportOptions, DataExportOptions
   import zipfile
   import json

   def test_build_manifest(export_service, mock_project_context):
       """Test manifest creation with correct fields."""
       manifest = export_service._build_manifest()

       assert manifest.project_name == "TestProject"
       assert manifest.slug == "testproject"
       assert manifest.app_version == "2.0"
       assert len(manifest.db_checksum_sha256) == 64  # SHA256 hex
       assert "result_set_count" in manifest.catalog_metadata

   def test_export_project_creates_valid_zip(export_service, tmp_path):
       """Test project export creates valid .rpsproj file."""
       output_path = tmp_path / "test_export.rpsproj"
       options = ProjectExportOptions(output_path=output_path)

       export_service.export_project(options)

       assert output_path.exists()

       # Verify zip contents
       with zipfile.ZipFile(output_path, 'r') as zf:
           names = zf.namelist()
           assert "manifest.json" in names
           assert "testproject.db" in names

           # Verify manifest structure
           manifest_data = json.loads(zf.read("manifest.json"))
           assert "project_name" in manifest_data
           assert "db_checksum_sha256" in manifest_data

   def test_export_data_per_table(export_service, tmp_path):
       """Test per-table data export creates correct files."""
       output_folder = tmp_path / "exports"
       options = DataExportOptions(
           result_set_ids=[1],
           result_types=["Drifts"],
           include_directions=["X", "Y"],
           format="excel",
           combine_mode="per_table",
           output_folder=output_folder,
       )

       export_service.export_data(options)

       assert (output_folder / "Drifts_X.xlsx").exists()
       assert (output_folder / "Drifts_Y.xlsx").exists()

   def test_export_data_combined_excel(export_service, tmp_path):
       """Test combined Excel export creates multi-sheet workbook."""
       output_file = tmp_path / "combined.xlsx"
       options = DataExportOptions(
           result_set_ids=[1],
           result_types=["Drifts"],
           include_directions=["X", "Y"],
           format="excel",
           combine_mode="combined",
           output_file=output_file,
       )

       export_service.export_data(options)

       assert output_file.exists()

       # Verify sheets
       df_dict = pd.read_excel(output_file, sheet_name=None)
       assert "Drifts_X" in df_dict
       assert "Drifts_Y" in df_dict

   def test_filename_building(export_service):
       """Test filename convention matches Old_scripts."""
       assert export_service._build_filename("Drifts", "X", "excel") == "Drifts_X.xlsx"
       assert export_service._build_filename("WallShears", "V2", "csv") == "WallShears_V2.csv"
       assert export_service._build_filename("Drifts", "X", "excel", "Max") == "Drifts_X_Max.xlsx"
       assert export_service._build_filename("QuadRotations", "", "excel") == "QuadRotations.xlsx"

   Deliverable:
   - ✅ src/services/export_service.py with domain models and logic
   - ✅ tests/services/test_export_service.py with unit tests

   ---
   Phase 3: Project Export Pipeline

   3.1 Manifest Schema

   Fields (minimal for display + re-import):
   {
     "project_name": "160Wil",
     "slug": "160wil",
     "description": "Office building - 160 Wilshire",
     "created_at": "2024-10-15T08:30:00Z",
     "exported_at": "2024-11-08T15:45:30Z",
     "app_version": "2.0",
     "db_filename": "160wil.db",
     "db_checksum_sha256": "a3f5c8...",
     "catalog_metadata": {
       "result_set_count": 3,
       "load_case_count": 120,
       "story_count": 8,
       "last_opened": "2024-11-07T09:00:00Z"
     }
   }

   Purpose of each field:
   - project_name, slug, description: Display in import wizard
   - created_at: Preserve original creation date
   - exported_at: Track when backup was made
   - app_version: Compatibility check (future: migration if schema changed)
   - db_checksum_sha256: Verify file integrity on import
   - catalog_metadata: Show project stats before importing

   3.2 Packaging Process

   def export_project(self, options: ProjectExportOptions,
                     progress_callback: Optional[Callable] = None) -> None:
       """Export complete project as .rpsproj bundle."""

       # Step 1: Build manifest (5%)
       if progress_callback:
           progress_callback("Building manifest...", 1, 20)
       manifest = self._build_manifest()

       # Step 2: Create zip archive (10%)
       if progress_callback:
           progress_callback("Creating archive...", 2, 20)

       with zipfile.ZipFile(options.output_path, 'w',
                           compression=zipfile.ZIP_DEFLATED,
                           compresslevel=options.compress_level) as zf:

           # Add manifest.json (15%)
           if progress_callback:
               progress_callback("Adding manifest...", 3, 20)
           zf.writestr("manifest.json", manifest.to_json())

           # Add database file (95% of work)
           if progress_callback:
               progress_callback("Adding database...", 5, 20)
           db_path = self.project_context.db_path
           zf.write(db_path, f"{manifest.slug}.db")

           # Complete (100%)
           if progress_callback:
               progress_callback("Export complete!", 20, 20)

   3.3 Integrity Verification

   def _calculate_file_checksum(self, file_path: Path) -> str:
       """Calculate SHA256 checksum of file for integrity verification."""
       sha256 = hashlib.sha256()
       with open(file_path, 'rb') as f:
           for chunk in iter(lambda: f.read(8192), b''):
               sha256.update(chunk)
       return sha256.hexdigest()

   Future import validation:
   # In future import wizard
   def validate_rpsproj(file_path: Path) -> bool:
       with zipfile.ZipFile(file_path, 'r') as zf:
           manifest = json.loads(zf.read("manifest.json"))

           # Extract DB to temp location
           temp_db = zf.extract(manifest["db_filename"])

           # Verify checksum
           actual_checksum = calculate_checksum(temp_db)
           expected_checksum = manifest["db_checksum_sha256"]

           if actual_checksum != expected_checksum:
               raise ValueError("Database file corrupted!")

           return True

   Deliverable:
   - ✅ Manifest schema finalized
   - ✅ Packaging logic in ExportService
   - ✅ Checksum validation implemented
   - ✅ Tests for archive integrity

   ---
   Phase 4: Data Export Pipeline

   4.1 ResultTableBuilder

   Purpose: Transform ResultDataService output into export-ready DataFrames

   class ResultTableBuilder:
       """Build export-ready tables from result datasets."""

       def __init__(self, result_service):
           self.result_service = result_service

       def build_global_result_table(self, result_type: str, direction: str,
                                    result_set_id: int) -> pd.DataFrame:
           """Build table for global result (Drifts, Accelerations, etc.)."""
           dataset = self.result_service.get_standard_dataset(
               result_type, direction, result_set_id
           )

           # Dataset.df is already in perfect format:
           # Columns: Story | TH01 | TH02 | MCR1 | ...
           return dataset.df

       def build_element_result_table(self, result_type: str, direction: str,
                                      result_set_id: int, element_id: int = 0) -> pd.DataFrame:
           """Build table for element result (WallShears, ColumnShears, etc.)."""
           dataset = self.result_service.get_element_dataset(
               result_type, direction, result_set_id, element_id
           )

           # Dataset.df format:
           # Columns: Element | Story | TH01 | TH02 | MCR1 | ...
           return dataset.df

       def build_maxmin_tables(self, result_type: str, direction: str,
                              result_set_id: int) -> tuple[pd.DataFrame, pd.DataFrame]:
           """Build Max and Min envelope tables."""
           maxmin_dataset = self.result_service.get_maxmin_dataset(
               result_type, direction, result_set_id
           )

           # maxmin_dataset.max_df: Story | TH01_Max | TH02_Max | ...
           # maxmin_dataset.min_df: Story | TH01_Min | TH02_Min | ...
           return maxmin_dataset.max_df, maxmin_dataset.min_df

       def get_all_result_types_for_set(self, result_set_id: int) -> dict:
           """Discover all available result types in a result set."""
           # Query cache to find what exists
           available = {
               "global": [],  # ["Drifts", "Accelerations", "Forces"]
               "elements": []  # ["WallShears", "ColumnShears"]
           }

           # Query GlobalResultsCache
           with self.result_service.session_scope() as session:
               global_types = session.query(GlobalResultsCache.result_type).filter(
                   GlobalResultsCache.result_set_id == result_set_id
               ).distinct().all()
               available["global"] = [rt[0] for rt in global_types]

               # Query ElementResultsCache
               element_types = session.query(ElementResultsCache.result_type).filter(
                   ElementResultsCache.result_set_id == result_set_id
               ).distinct().all()
               available["elements"] = [rt[0] for rt in element_types]

           return available

   Key Insight: ResultDataService already returns DataFrames in the exact format needed for export! No transformation required.

   4.2 Writing Strategies

   Per-Table Strategy (default):
   def _export_per_table(self, options: DataExportOptions, progress_callback=None):
       """Export each result type/direction to separate file."""

       for result_type in options.result_types:
           for direction in self._get_directions(result_type):
               # Build filename
               filename = f"{result_type}_{direction}.{ext}"
               file_path = options.output_folder / filename

               # Get data
               df = self.table_builder.build_global_result_table(
                   result_type, direction, result_set_id
               )

               # Write file
               if options.format == "excel":
                   df.to_excel(file_path, index=False)
               else:  # csv
                   df.to_csv(file_path, index=False)

               # Progress update
               progress_callback(f"Exported {filename}", current, total)

   Combined Excel Strategy:
   def _export_combined_excel(self, options: DataExportOptions, progress_callback=None):
       """Export all results to single multi-sheet Excel workbook."""

       with pd.ExcelWriter(options.output_file, engine='openpyxl') as writer:
           for result_type in options.result_types:
               for direction in self._get_directions(result_type):
                   # Get data
                   df = self.table_builder.build_global_result_table(
                       result_type, direction, result_set_id
                   )

                   # Write to sheet
                   sheet_name = f"{result_type}_{direction}"
                   df.to_excel(writer, sheet_name=sheet_name, index=False)

                   # Also export Max/Min if requested
                   if options.include_maxmin:
                       max_df, min_df = self.table_builder.build_maxmin_tables(...)
                       max_df.to_excel(writer, sheet_name=f"{sheet_name}_Max", index=False)
                       min_df.to_excel(writer, sheet_name=f"{sheet_name}_Min", index=False)

   4.3 Scope Filtering

   Current View Only:
   # User clicked "Export" with Drifts_X currently displayed
   options = DataExportOptions(
       result_set_ids=[current_result_set_id],
       result_types=[current_result_type],  # "Drifts"
       include_directions=[current_direction],  # "X"
       format="excel",
       combine_mode="per_table",
       output_folder=selected_folder,
   )

   All Result Types for Current Set:
   # Discover all available types
   available = table_builder.get_all_result_types_for_set(current_result_set_id)

   options = DataExportOptions(
       result_set_ids=[current_result_set_id],
       result_types=available["global"] + available["elements"],
       include_directions=["X", "Y", "V2", "V3", "UX", "UY", "VX", "VY"],  # All
       format="excel",
       combine_mode="combined",  # Multi-sheet workbook
       output_file=selected_file,
   )

   Multiple Result Sets:
   # User selected DES, MCE, SLE from checkbox list
   options = DataExportOptions(
       result_set_ids=[1, 2, 3],  # DES, MCE, SLE
       result_types=user_selected_types,  # From dialog checkboxes
       include_directions=["X", "Y"],
       format="excel",
       combine_mode="per_table",
       output_folder=selected_folder,
   )

   Deliverable:
   - ✅ ResultTableBuilder for data transformation
   - ✅ Per-table and combined export strategies
   - ✅ Scope filtering (current/all/multiple)
   - ✅ Tests mocking repositories and asserting DataFrame structure

   ---
   Phase 5: GUI Workflow

   5.1 Export Data Dialog

   File: src/gui/export_dialog.py (~500 lines total for both dialogs)

   class ExportDataDialog(QDialog):
       """Dialog for exporting result data (Old_scripts format)."""

       def __init__(self, project_id, project_name, result_service,
                    current_result_set_id, current_result_type, current_direction, parent=None):
           super().__init__(parent)
           self.project_id = project_id
           self.project_name = project_name
           self.result_service = result_service
           self.current_result_set_id = current_result_set_id
           self.current_result_type = current_result_type
           self.current_direction = current_direction

           self.setWindowTitle("Export Result Data")
           self.setMinimumWidth(650)
           self.setMinimumHeight(550)

           self._setup_ui()

       def _setup_ui(self):
           """Build dialog UI."""
           layout = QVBoxLayout(self)
           layout.setSpacing(16)
           layout.setContentsMargins(24, 24, 24, 24)

           # === Export Scope ===
           scope_group = QGroupBox("Export Scope")
           scope_layout = QVBoxLayout()

           self.current_view_radio = QRadioButton(
               f"Current view only ({self.current_result_type}_{self.current_direction})"
           )
           self.current_view_radio.setChecked(True)
           self.current_view_radio.toggled.connect(self._on_scope_changed)
           scope_layout.addWidget(self.current_view_radio)

           self.all_types_radio = QRadioButton("All result types for current result set")
           self.all_types_radio.toggled.connect(self._on_scope_changed)
           scope_layout.addWidget(self.all_types_radio)

           self.multiple_sets_radio = QRadioButton("Multiple result sets")
           self.multiple_sets_radio.toggled.connect(self._on_scope_changed)
           scope_layout.addWidget(self.multiple_sets_radio)

           scope_group.setLayout(scope_layout)
           layout.addWidget(scope_group)

           # === Result Type Selector (initially hidden) ===
           self.result_selector_widget = self._create_result_selector()
           self.result_selector_widget.setVisible(False)
           layout.addWidget(self.result_selector_widget)

           # === Export Options ===
           options_group = QGroupBox("Export Options")
           options_layout = QVBoxLayout()

           # Format selection
           format_layout = QHBoxLayout()
           format_layout.addWidget(QLabel("Format:"))

           self.excel_radio = QRadioButton("Excel (.xlsx)")
           self.excel_radio.setChecked(True)
           self.excel_radio.toggled.connect(self._on_format_changed)
           format_layout.addWidget(self.excel_radio)

           self.csv_radio = QRadioButton("CSV (.csv)")
           format_layout.addWidget(self.csv_radio)
           format_layout.addStretch()
           options_layout.addLayout(format_layout)

           # Combine mode (Excel only)
           self.combine_check = QCheckBox("Combine into single file (Excel multi-sheet)")
           self.combine_check.setToolTip("Create one Excel workbook with multiple sheets")
           options_layout.addWidget(self.combine_check)

           # Max/Min envelopes
           self.maxmin_check = QCheckBox("Include Max/Min envelopes")
           self.maxmin_check.setChecked(True)
           self.maxmin_check.setToolTip("Export separate Max and Min envelope files")
           options_layout.addWidget(self.maxmin_check)

           options_group.setLayout(options_layout)
           layout.addWidget(options_group)

           # === Output Path ===
           output_group = QGroupBox("Output Location")
           output_layout = QVBoxLayout()

           path_layout = QHBoxLayout()
           self.output_path_edit = QLineEdit()
           self.output_path_edit.setPlaceholderText("Select output folder or file...")
           self.output_path_edit.setProperty("empty", "true")
           path_layout.addWidget(self.output_path_edit)

           self.browse_btn = create_styled_button("Browse...", "secondary", "sm")
           self.browse_btn.clicked.connect(self._browse_output)
           path_layout.addWidget(self.browse_btn)

           output_layout.addLayout(path_layout)
           output_group.setLayout(output_layout)
           layout.addWidget(output_group)

           # === Progress ===
           self.progress_bar = QProgressBar()
           self.progress_bar.setVisible(False)
           layout.addWidget(self.progress_bar)

           self.status_label = QLabel("")
           self.status_label.setVisible(False)
           layout.addWidget(self.status_label)

           # === Buttons ===
           button_layout = QHBoxLayout()
           button_layout.addStretch()

           export_btn = create_styled_button("Export", "primary", "md")
           export_btn.clicked.connect(self._start_export)
           button_layout.addWidget(export_btn)

           cancel_btn = create_styled_button("Cancel", "secondary", "md")
           cancel_btn.clicked.connect(self.reject)
           button_layout.addWidget(cancel_btn)

           layout.addLayout(button_layout)

           # Apply GMP styling
           self._apply_styling()

       def _create_result_selector(self):
           """Create result type selector tree."""
           widget = QWidget()
           layout = QVBoxLayout(widget)

           # Tree widget with checkboxes
           self.result_tree = QTreeWidget()
           self.result_tree.setHeaderLabel("Select Result Types to Export")
           self.result_tree.setColumnCount(1)

           # Global Results section
           global_item = QTreeWidgetItem(["Global Results"])
           global_item.setFlags(global_item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
           global_item.setCheckState(0, Qt.CheckState.Checked)

           for result_type in ["Drifts", "Accelerations", "Forces", "Displacements"]:
               type_item = QTreeWidgetItem(global_item, [result_type])
               type_item.setFlags(type_item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
               type_item.setCheckState(0, Qt.CheckState.Checked)

               # Add direction children
               for direction in ["X", "Y"]:
                   dir_item = QTreeWidgetItem(type_item, [direction])
                   dir_item.setFlags(dir_item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
                   dir_item.setCheckState(0, Qt.CheckState.Checked)

           self.result_tree.addTopLevelItem(global_item)
           global_item.setExpanded(True)

           # Element Results section
           element_item = QTreeWidgetItem(["Element Results"])
           element_item.setFlags(element_item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
           element_item.setCheckState(0, Qt.CheckState.Checked)

           for result_type in ["WallShears", "QuadRotations", "ColumnShears"]:
               type_item = QTreeWidgetItem(element_item, [result_type])
               type_item.setFlags(type_item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
               type_item.setCheckState(0, Qt.CheckState.Checked)

           self.result_tree.addTopLevelItem(element_item)
           element_item.setExpanded(True)

           layout.addWidget(self.result_tree)

           return widget

       def _on_scope_changed(self):
           """Handle export scope radio button change."""
           show_selector = not self.current_view_radio.isChecked()
           self.result_selector_widget.setVisible(show_selector)

       def _on_format_changed(self):
           """Handle format radio button change."""
           is_excel = self.excel_radio.isChecked()
           self.combine_check.setEnabled(is_excel)
           if not is_excel:
               self.combine_check.setChecked(False)

       def _browse_output(self):
           """Open file/folder browser."""
           is_combined = self.combine_check.isChecked() and self.excel_radio.isChecked()

           if is_combined:
               # Single file
               suggested_name = f"{self.project_name}_Results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
               file_path, _ = QFileDialog.getSaveFileName(
                   self,
                   "Save Export File",
                   str(Path.home() / suggested_name),
                   "Excel Files (*.xlsx)",
               )
               if file_path:
                   self.output_path_edit.setText(file_path)
           else:
               # Folder
               folder = QFileDialog.getExistingDirectory(
                   self,
                   "Select Export Folder",
                   str(Path.home()),
               )
               if folder:
                   self.output_path_edit.setText(folder)

           # Update border color
           self._update_empty_state()

       def _update_empty_state(self):
           """Update border color based on path presence."""
           is_empty = not self.output_path_edit.text().strip()
           self.output_path_edit.setProperty("empty", "true" if is_empty else "false")
           self.output_path_edit.style().unpolish(self.output_path_edit)
           self.output_path_edit.style().polish(self.output_path_edit)

       def _start_export(self):
           """Start export process."""
           # Validate output path
           if not self.output_path_edit.text().strip():
               QMessageBox.warning(self, "Export Error", "Please select an output location.")
               return

           # Build export options
           options = self._build_export_options()

           # Show progress
           self.progress_bar.setVisible(True)
           self.status_label.setVisible(True)

           # Start worker thread
           self.worker = ExportDataWorker(self.result_service, options)
           self.worker.progress.connect(self._on_progress)
           self.worker.finished.connect(self._on_finished)
           self.worker.start()

       def _build_export_options(self) -> DataExportOptions:
           """Build DataExportOptions from dialog state."""
           # Determine scope
           if self.current_view_radio.isChecked():
               result_types = [self.current_result_type]
               directions = [self.current_direction]
               result_set_ids = [self.current_result_set_id]
           else:
               # Parse tree selections
               result_types, directions = self._get_selected_result_types()
               result_set_ids = [self.current_result_set_id]  # TODO: Multi-set support

           # Determine format
           format = "excel" if self.excel_radio.isChecked() else "csv"
           combine_mode = "combined" if self.combine_check.isChecked() else "per_table"

           # Output path
           output_path = Path(self.output_path_edit.text())
           if combine_mode == "combined":
               output_file = output_path
               output_folder = None
           else:
               output_file = None
               output_folder = output_path

           return DataExportOptions(
               result_set_ids=result_set_ids,
               result_types=result_types,
               include_directions=directions,
               include_maxmin=self.maxmin_check.isChecked(),
               format=format,
               combine_mode=combine_mode,
               output_folder=output_folder,
               output_file=output_file,
           )

       def _get_selected_result_types(self):
           """Parse tree to get selected result types and directions."""
           result_types = []
           directions = []
           # TODO: Implement tree parsing
           return result_types, directions

       def _on_progress(self, message, current, total):
           """Handle progress update from worker."""
           self.progress_bar.setMaximum(total)
           self.progress_bar.setValue(current)
           self.status_label.setText(message)

       def _on_finished(self, success, message):
           """Handle export completion."""
           self.progress_bar.setVisible(False)
           self.status_label.setVisible(False)

           if success:
               QMessageBox.information(self, "Export Complete", message)
               self.accept()
           else:
               QMessageBox.critical(self, "Export Failed", message)

       def _apply_styling(self):
           """Apply GMP design system styling."""
           self.setStyleSheet(f"""
               QGroupBox {{
                   font-size: 14px;
                   font-weight: 600;
                   color: #d1d5db;
                   border: 1px solid #2c313a;
                   border-radius: 6px;
                   margin-top: 12px;
                   padding: 16px;
                   background-color: rgba(255, 255, 255, 0.02);
               }}
               QGroupBox::title {{
                   subcontrol-origin: margin;
                   left: 12px;
                   padding: 0 8px;
               }}
               QLineEdit[empty="true"] {{
                   border: 1px solid #ff8c00;  /* Orange for empty */
               }}
               QLineEdit:focus {{
                   border: 1px solid #4a7d89;  /* Teal for focus */
               }}
               QCheckBox {{
                   color: #d1d5db;
                   spacing: 8px;
               }}
               QRadioButton {{
                   color: #d1d5db;
                   spacing: 8px;
               }}
           """)

   class ExportDataWorker(QThread):
       """Background worker for data export."""
       progress = pyqtSignal(str, int, int)
       finished = pyqtSignal(bool, str)

       def __init__(self, result_service, options: DataExportOptions):
           super().__init__()
           self.result_service = result_service
           self.options = options

       def run(self):
           """Execute export in background."""
           try:
               export_service = ExportService(
                   project_context=None,  # TODO: Pass context
                   result_service=self.result_service
               )

               export_service.export_data(
                   self.options,
                   progress_callback=self._emit_progress
               )

               self.finished.emit(True, "Export completed successfully!")
           except Exception as e:
               self.finished.emit(False, f"Export failed: {str(e)}")

       def _emit_progress(self, message, current, total):
           """Emit progress signal."""
           self.progress.emit(message, current, total)

   5.2 Export Project Dialog

   class ExportProjectDialog(QDialog):
       """Dialog for exporting complete project (.rpsproj)."""

       def __init__(self, project_id, project_name, session_factory, parent=None):
           super().__init__(parent)
           self.project_id = project_id
           self.project_name = project_name
           self.session_factory = session_factory

           self.setWindowTitle("Export Project")
           self.setMinimumWidth(550)

           self._setup_ui()

       def _setup_ui(self):
           """Build dialog UI."""
           layout = QVBoxLayout(self)
           layout.setSpacing(16)
           layout.setContentsMargins(24, 24, 24, 24)

           # Info label
           info_label = QLabel(
               "Export complete project as .rpsproj file for backup or transfer to another device."
           )
           info_label.setWordWrap(True)
           info_label.setStyleSheet("color: #9ca3af; font-size: 13px;")
           layout.addWidget(info_label)

           # === Output File ===
           file_group = QGroupBox("Export File")
           file_layout = QHBoxLayout()

           self.file_path_edit = QLineEdit()
           self.file_path_edit.setPlaceholderText("Select destination file...")
           self.file_path_edit.setProperty("empty", "true")
           file_layout.addWidget(self.file_path_edit)

           browse_btn = create_styled_button("Browse...", "secondary", "sm")
           browse_btn.clicked.connect(self._browse_file)
           file_layout.addWidget(browse_btn)

           file_group.setLayout(file_layout)
           layout.addWidget(file_group)

           # === Include Options ===
           options_group = QGroupBox("Include in Export")
           options_layout = QVBoxLayout()

           self.include_metadata_check = QCheckBox("Project metadata (required)")
           self.include_metadata_check.setChecked(True)
           self.include_metadata_check.setEnabled(False)
           options_layout.addWidget(self.include_metadata_check)

           self.include_database_check = QCheckBox("Complete database (required)")
           self.include_database_check.setChecked(True)
           self.include_database_check.setEnabled(False)
           options_layout.addWidget(self.include_database_check)

           options_group.setLayout(options_layout)
           layout.addWidget(options_group)

           # === Progress ===
           self.progress_bar = QProgressBar()
           self.progress_bar.setVisible(False)
           layout.addWidget(self.progress_bar)

           self.status_label = QLabel("")
           self.status_label.setVisible(False)
           layout.addWidget(self.status_label)

           # === Buttons ===
           button_layout = QHBoxLayout()
           button_layout.addStretch()

           export_btn = create_styled_button("Export Project", "primary", "md")
           export_btn.clicked.connect(self._start_export)
           button_layout.addWidget(export_btn)

           cancel_btn = create_styled_button("Cancel", "secondary", "md")
           cancel_btn.clicked.connect(self.reject)
           button_layout.addWidget(cancel_btn)

           layout.addLayout(button_layout)

       def _browse_file(self):
           """Open file browser for .rpsproj file."""
           suggested_name = f"{self.project_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.rpsproj"

           file_path, _ = QFileDialog.getSaveFileName(
               self,
               "Save Project Export",
               str(Path.home() / suggested_name),
               "RPS Project Files (*.rpsproj)",
           )

           if file_path:
               self.file_path_edit.setText(file_path)
               self._update_empty_state()

       def _update_empty_state(self):
           """Update border color."""
           is_empty = not self.file_path_edit.text().strip()
           self.file_path_edit.setProperty("empty", "true" if is_empty else "false")
           self.file_path_edit.style().unpolish(self.file_path_edit)
           self.file_path_edit.style().polish(self.file_path_edit)

       def _start_export(self):
           """Start project export."""
           if not self.file_path_edit.text().strip():
               QMessageBox.warning(self, "Export Error", "Please select an output file.")
               return

           options = ProjectExportOptions(
               output_path=Path(self.file_path_edit.text())
           )

           self.progress_bar.setVisible(True)
           self.status_label.setVisible(True)

           self.worker = ExportProjectWorker(self.session_factory, options, self.project_id)
           self.worker.progress.connect(self._on_progress)
           self.worker.finished.connect(self._on_finished)
           self.worker.start()

       def _on_progress(self, message, current, total):
           """Handle progress update."""
           self.progress_bar.setMaximum(total)
           self.progress_bar.setValue(current)
           self.status_label.setText(message)

       def _on_finished(self, success, message):
           """Handle export completion."""
           self.progress_bar.setVisible(False)
           self.status_label.setVisible(False)

           if success:
               QMessageBox.information(self, "Export Complete", message)
               self.accept()
           else:
               QMessageBox.critical(self, "Export Failed", message)

   5.3 Integration with ProjectDetailWindow

   File: src/gui/project_detail_window.py

   Update line 874 (existing placeholder):
   def export_results(self):
       """Export results to file - show export dialog."""
       from gui.export_dialog import ExportDataDialog

       dialog = ExportDataDialog(
           project_id=self.project_id,
           project_name=self.project_name,
           result_service=self.result_service,
           current_result_set_id=self.current_result_set_id,
           current_result_type=self.current_result_type,
           current_direction=self.current_direction,
           parent=self
       )

       if dialog.exec():
           self.statusBar().showMessage("Export completed successfully!", 3000)

   Add after line 172 (new Export Project button):
   # Export Project button
   export_project_btn = create_styled_button("Export Project", "secondary", "sm")
   export_project_btn.setToolTip("Export complete project database")
   export_project_btn.clicked.connect(self.export_project)
   layout.addWidget(export_project_btn)

   # ... (later in class)

   def export_project(self):
       """Export complete project database."""
       from gui.export_dialog import ExportProjectDialog

       dialog = ExportProjectDialog(
           project_id=self.project_id,
           project_name=self.project_name,
           session_factory=self.session_factory,
           parent=self
       )

       if dialog.exec():
           self.statusBar().showMessage("Project exported successfully!", 3000)

   Deliverable:
   - ✅ ExportDataDialog with result type selector
   - ✅ ExportProjectDialog with file picker
   - ✅ Background workers for non-blocking export
   - ✅ Integration with ProjectDetailWindow

   ---
   Phase 6: Validation & Documentation

   6.1 Integration Tests

   File: tests/integration/test_export_integration.py (~150 lines)

   def test_export_project_end_to_end(test_project):
       """Test complete project export pipeline."""
       # Export project
       export_service = ExportService(test_project.context, None)
       output_path = tmp_path / "test.rpsproj"

       options = ProjectExportOptions(output_path=output_path)
       export_service.export_project(options)

       # Verify archive
       assert output_path.exists()

       with zipfile.ZipFile(output_path, 'r') as zf:
           manifest = json.loads(zf.read("manifest.json"))
           assert manifest["project_name"] == test_project.name
           assert manifest["slug"] == test_project.slug

           # Verify DB present
           assert f"{test_project.slug}.db" in zf.namelist()

   def test_export_data_per_table(test_project, result_service):
       """Test data export creates correct files."""
       export_service = ExportService(test_project.context, result_service)

       options = DataExportOptions(
           result_set_ids=[1],
           result_types=["Drifts"],
           include_directions=["X", "Y"],
           format="excel",
           combine_mode="per_table",
           output_folder=tmp_path / "exports"
       )

       export_service.export_data(options)

       assert (tmp_path / "exports" / "Drifts_X.xlsx").exists()
       assert (tmp_path / "exports" / "Drifts_Y.xlsx").exists()

       # Verify content
       df = pd.read_excel(tmp_path / "exports" / "Drifts_X.xlsx")
       assert "Story" in df.columns
       assert len(df) > 0  # Has data

   def test_export_combined_excel(test_project, result_service):
       """Test combined Excel export creates multi-sheet workbook."""
       export_service = ExportService(test_project.context, result_service)

       options = DataExportOptions(
           result_set_ids=[1],
           result_types=["Drifts", "Accelerations"],
           include_directions=["X"],
           format="excel",
           combine_mode="combined",
           output_file=tmp_path / "combined.xlsx"
       )

       export_service.export_data(options)

       # Verify sheets
       wb = openpyxl.load_workbook(tmp_path / "combined.xlsx")
       assert "Drifts_X" in wb.sheetnames
       assert "Accelerations_X" in wb.sheetnames

   6.2 CLI Smoke Script

   File: scripts/cli_export.py (~100 lines)

   #!/usr/bin/env python
   """CLI script for testing exports during development."""

   import argparse
   from pathlib import Path
   from services.export_service import ExportService, ProjectExportOptions, DataExportOptions
   from services.project_service import ProjectService

   def export_project_cli(project_name: str, output_path: str):
       """Export project via CLI."""
       project_service = ProjectService()
       context = project_service.get_project_context(project_name)

       export_service = ExportService(context, None)
       options = ProjectExportOptions(output_path=Path(output_path))

       print(f"Exporting project '{project_name}' to {output_path}...")
       export_service.export_project(options, progress_callback=print_progress)
       print("✅ Export complete!")

   def export_data_cli(project_name: str, result_set_name: str, output_folder: str):
       """Export data via CLI."""
       # ... implementation
       print(f"Exporting data for '{project_name}' / '{result_set_name}'...")
       # ...

   def print_progress(message, current, total):
       """Print progress to console."""
       percent = int((current / total) * 100)
       print(f"[{percent}%] {message}")

   if __name__ == "__main__":
       parser = argparse.ArgumentParser(description="Export RPS projects")
       parser.add_argument("--project", required=True, help="Project name")
       parser.add_argument("--mode", choices=["project", "data"], required=True)
       parser.add_argument("--output", required=True, help="Output path")

       args = parser.parse_args()

       if args.mode == "project":
           export_project_cli(args.project, args.output)
       else:
           export_data_cli(args.project, "DES", args.output)

   6.3 Documentation Updates

   Update CLAUDE.md - Add export examples:
   ### Exporting Data

   **Export current view**:
   1. Open project detail window
   2. Navigate to desired result type/direction
   3. Click "Export Results" button
   4. Select output format (Excel/CSV)
   5. Choose destination folder or file

   **Export all result types**:
   1. In export dialog, select "All result types for current result set"
   2. Choose result types from tree
   3. Select "Combine into single file" for Excel multi-sheet
   4. Export creates organized folder or single workbook

   **Export complete project**:
   1. Click "Export Project" button
   2. Choose destination for .rpsproj file
   3. Archive includes database + manifest
   4. Can be re-imported on another device

   **File naming** (matches Old_scripts):
   - Per-table: `Drifts_X.xlsx`, `WallShears_V2.csv`
   - Max/Min: `Drifts_X_Max.xlsx`, `Drifts_X_Min.xlsx`
   - Combined: `160Wil_DES_20241108.xlsx` (multi-sheet)

   Update ARCHITECTURE.md - Document export architecture:
   ### Export Architecture (v2.0)

   **Export Service** (`services/export_service.py`):
   - Business logic for project and data export
   - Manifest generation with checksums
   - DataFrame transformation via ResultDataService
   - Progress tracking callbacks

   **Export Dialogs** (`gui/export_dialog.py`):
   - ExportDataDialog - Result tables export
   - ExportProjectDialog - Complete project backup
   - Background workers prevent UI freeze
   - GMP design system styling

   **File Formats**:
   - Project: `.rpsproj` (ZIP with manifest.json + database)
   - Data: Excel (.xlsx) or CSV (.csv)
   - Combined: Multi-sheet Excel workbooks

   **Re-import** (future):
   - Import wizard in Projects window
   - Manifest validation (checksum, version)
   - Catalog entry creation
   - Database extraction to data/projects/

   Create: docs/implementation/EXPORT_SPECIFICATION.md - Full specification document

   Deliverable:
   - ✅ Integration tests covering end-to-end workflows
   - ✅ CLI smoke script for development testing
   - ✅ CLAUDE.md usage examples
   - ✅ ARCHITECTURE.md architecture documentation
   - ✅ EXPORT_SPECIFICATION.md full spec

   ---
   Implementation Timeline

   Sprint 1: Foundation (8 hours)

   - Day 1-2: Export service domain models and core logic
   - Implement ExportService with project and data export methods
   - Write unit tests for ExportService
   - Deliverables: export_service.py, test_export_service.py

   Sprint 2: Data Export (6 hours)

   - Day 3: Implement per-table export strategy
   - Day 4: Implement combined Excel export
   - Add Max/Min envelope support
   - Test with real project data
   - Deliverables: Working data export pipeline

   Sprint 3: GUI (8 hours)

   - Day 5: ExportDataDialog UI
   - Day 6: ExportProjectDialog UI
   - Background workers
   - Integration with ProjectDetailWindow
   - Deliverables: export_dialog.py, updated project_detail_window.py

   Sprint 4: Polish & Validation (6 hours)

   - Day 7: Integration tests
   - Day 8: CLI smoke script, documentation
   - Bug fixes and edge cases
   - Deliverables: Complete, tested feature

   Total Effort: ~28 hours (3.5 developer days)

   ---
   Success Criteria

   ✅ Export Project creates valid .rpsproj file with manifest + database
   ✅ Manifest includes checksum for integrity validation
   ✅ Export Data (per-table) creates files matching Old_scripts naming
   ✅ Export Data (combined) creates multi-sheet Excel workbook
   ✅ CSV export works for per-table mode
   ✅ Max/Min envelopes export as separate files
   ✅ Progress bar updates during large exports (no UI freeze)
   ✅ Background workers prevent blocking
   ✅ File naming convention matches Old_scripts exactly
   ✅ DataFrames exported match current table view format
   ✅ Error messages clear and actionable
   ✅ Documentation updated (CLAUDE.md, ARCHITECTURE.md)
   ✅ Integration tests pass
   ✅ CLI smoke script works for manual testing

   ---
   Open Questions Resolved

   1. ✅ CSV combined exports: Not supported (only Excel multi-sheet)
   2. ✅ Project export scope: SQLite DB + manifest only (sufficient for re-import)
   3. ✅ Import feature location: Projects window (Main window)
   4. ✅ Data export scope: Display data only (no raw ETABS metadata)
   5. ✅ Old scripts format: One file per result type/direction with all load cases

   ---
   Future Enhancements (Post-Implementation)

   Phase 7 (Future): Import Project Wizard
   - Add "Import Project" button to Main window Projects page
   - Dialog: Select .rpsproj file → validate manifest → show preview
   - Extract DB to data/projects/{slug}/{slug}.db
   - Create catalog entry from manifest metadata
   - Refresh project list automatically

   Phase 8 (Future): Advanced Export Options
   - Export filtered subsets (date range, specific load cases)
   - Export plots as images (PNG/PDF)
   - Custom templates for report generation
   - Batch export multiple projects
   - Scheduled/automated exports

   ---
   Files Summary

   New Files (3):
   1. src/services/export_service.py (~400 lines)
   2. src/gui/export_dialog.py (~500 lines)
   3. docs/implementation/EXPORT_SPECIFICATION.md (~50 lines)

   Modified Files (3):
   1. src/gui/project_detail_window.py (+30 lines)
   2. CLAUDE.md (+20 lines)
   3. ARCHITECTURE.md (+30 lines)

   Test Files (2):
   1. tests/services/test_export_service.py (~200 lines)
   2. tests/integration/test_export_integration.py (~150 lines)

   Scripts (1):
   1. scripts/cli_export.py (~100 lines)

   Total New Code: ~1,480 lines
   Total Test Code: ~350 lines

   ---
   Dependencies

   ✅ pandas - DataFrame manipulation and Excel/CSV writing
   ✅ openpyxl - Excel file creation (already installed)
   ✅ PyQt6 - Dialogs and background workers (already installed)
   ✅ zipfile - Standard library (no install needed)
   ✅ hashlib - Standard library (no install needed)
   ✅ json - Standard library (no install needed)


• Plan Review Findings

  - ExportService._build_manifest() relies on self.project_context.session_scope() and a globally constructed CatalogRepository, but neither exists today.
    ProjectContext (src/services/project_service.py:26) only exposes session()/session_factory(), so you’ll blow up with AttributeError. The catalog repo
    also needs an initialized session—plan should inject sessions or reuse existing repositories instead of calling parameterless constructors.
  - The manifest step says it will query ResultSet, LoadCase, and Story counts directly, yet no ORM models are imported in the plan. Make sure the service
    can reach those tables without creating new dependency tangles (or reuse the counts already exposed by ProjectDetailWindow).
  - ResultDataService.get_maxmin_dataset() signature is (result_set_id, base_result_type='Drifts') (src/processing/result_service/service.py:101). Plan
    calls it as get_maxmin_dataset(result_type, direction, result_set_id), which swaps arguments and injects a direction that method doesn’t accept. Similar
    issue for element exports: plan never distinguishes between base result types and direction-specific cache keys, so filenames/sheet names will drift
    from actual dataset keys.
  - CSV scope handling ignores that some result types don’t have directions (e.g., QuadRotations, MinAxial). A single include_directions=["X","Y"] applied
    uniformly will request datasets that don’t exist. Need per-result-type direction resolution, likely sourced from RESULT_CONFIGS.
  - UI integration references self.session_factory in ProjectDetailWindow.export_project(), but that class doesn’t define such an attribute. You only have
    context.session() today. Either store context.session_factory() in the constructor or change the dialog API.
  - The plan assumes ResultDataService exposes session_scope() and direct access to cache tables (GlobalResultsCache, etc.), but that helper doesn’t exist.
    Discovering available result types will need new repository methods rather than ad-hoc session queries.
  - The estimated line counts/new files tally to ~1,500 lines for a single feature, which is very high. Consider splitting into smaller deliverables or
    reusing existing dialogs/components to stay aligned with the repo’s current scale.


    Now I will like to add another feature at the project level which will allow me to compare results wise different results set eg. Eg for the drifts all any other global results type I would like to see a comparison plot and tables for the average drifts in X direction. The same for individual results types in elements category. Lets create a plan for this