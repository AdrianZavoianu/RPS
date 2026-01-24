# Excel-Based Project Export/Import Implementation Plan

## Overview

Implement Excel-based project export/import with human-readable sheets and hidden JSON metadata for re-import.

**Format**: Single `.xlsx` workbook with multiple sheets
**Use Cases**:
1. Backup/restore projects
2. Share projects with colleagues
3. Inspect/analyze data in Excel
4. Transfer projects between devices
5. Manual data editing if needed

---

## Excel Workbook Structure

### Sheet 1: README (Visible)

Human-readable project overview:

```
PROJECT INFORMATION
===================

Project Name:        160 Wilshire
Description:         Office building - seismic analysis
Created:             2024-10-15 08:30:00
Exported:            2024-11-08 15:45:30
RPS Version:         2.1

DATABASE SUMMARY
================

Result Sets:         3 (DES, MCE, SLE)
Load Cases:          120
Stories:             8
Elements:            45 (Walls: 12, Columns: 25, Beams: 8)

RESULTS INCLUDED
================

Global Results:      Drifts (X, Y), Accelerations (X, Y), Forces (X, Y)
Element Results:     Wall Shears (V2, V3), Quad Rotations, Column Shears (V2, V3)

IMPORT INSTRUCTIONS
===================

To import this project into RPS:
1. Open RPS application
2. Click "Import Project" on Projects page
3. Select this Excel file
4. Review project summary
5. Click "Import"

The hidden "IMPORT_DATA" sheet contains metadata required for re-import.
Do NOT delete or modify this sheet.
```

### Sheet 2: Result Sets (Visible)

```
| Name | Description           | Created At          |
|------|-----------------------|---------------------|
| DES  | Design Basis          | 2024-10-15 09:00:00 |
| MCE  | Maximum Credible      | 2024-10-15 09:15:00 |
| SLE  | Service Level         | 2024-10-15 09:30:00 |
```

### Sheet 3: Load Cases (Visible)

```
| Name  | Description                    |
|-------|--------------------------------|
| TH01  | Time History 1                 |
| TH02  | Time History 2                 |
| MCR1  | Modal Combination Rule 1       |
| ...   | ...                            |
```

### Sheet 4: Stories (Visible)

```
| Name   | Sort Order | Elevation (m) |
|--------|------------|---------------|
| Base   | 0          | 0.0           |
| S1     | 1          | 4.5           |
| S2     | 2          | 8.0           |
| ...    | ...        | ...           |
```

### Sheet 5: Elements (Visible)

```
| Name    | Unique Name | Element Type |
|---------|-------------|--------------|
| P1      | Pier 1      | Wall         |
| P2      | Pier 2      | Wall         |
| C1      | Column 1    | Column       |
| ...     | ...         | ...          |
```

### Sheets 6+: Result Data (Visible)

One sheet per result type with actual data:

**Drifts_X Sheet**:
```
| Story | TH01  | TH02  | MCR1  | MCR2  | ... |
|-------|-------|-------|-------|-------|-----|
| S8    | 0.45  | 0.52  | 0.38  | 0.41  | ... |
| S7    | 0.58  | 0.64  | 0.49  | 0.53  | ... |
| S6    | 0.71  | 0.78  | 0.61  | 0.66  | ... |
| ...   | ...   | ...   | ...   | ...   | ... |
```

**WallShears_V2 Sheet** (element results):
```
| Element | Story | TH01    | TH02    | MCR1    | ... |
|---------|-------|---------|---------|---------|-----|
| P1      | S8    | 1250.5  | 1320.8  | 1180.2  | ... |
| P1      | S7    | 1580.3  | 1650.9  | 1490.7  | ... |
| P2      | S8    | 980.2   | 1050.6  | 920.4   | ... |
| ...     | ...   | ...     | ...     | ...     | ... |
```

### Final Sheet: IMPORT_DATA (Hidden)

JSON metadata for re-import:

```json
{
  "version": "2.1",
  "export_timestamp": "2024-11-08T15:45:30Z",
  "project": {
    "name": "160 Wilshire",
    "slug": "160wil",
    "description": "Office building - seismic analysis",
    "created_at": "2024-10-15T08:30:00Z"
  },
  "result_sets": [
    {
      "name": "DES",
      "description": "Design Basis",
      "created_at": "2024-10-15T09:00:00Z"
    }
  ],
  "load_cases": [
    {"name": "TH01", "description": "Time History 1"},
    {"name": "TH02", "description": "Time History 2"}
  ],
  "stories": [
    {"name": "Base", "sort_order": 0, "elevation": 0.0},
    {"name": "S1", "sort_order": 1, "elevation": 4.5}
  ],
  "elements": [
    {"name": "P1", "unique_name": "Pier 1", "element_type": "Wall"},
    {"name": "P2", "unique_name": "Pier 2", "element_type": "Wall"}
  ],
  "result_sheet_mapping": {
    "global": ["Drifts_X", "Drifts_Y", "Accelerations_X"],
    "element": ["WallShears_V2", "WallShears_V3", "QuadRotations"]
  },
  "checksum": "sha256_hash_of_data_sheets_combined"
}
```

---

## Implementation Details

### 1.1 Export Service - Excel Project Export

**File**: `src/services/export_service.py`

```python
@dataclass
class ProjectExportExcelOptions:
    """Options for Excel project export."""
    output_path: Path
    include_all_results: bool = True
    result_set_ids: Optional[List[int]] = None  # None = all

class ExportService:
    # ... existing code ...

    APP_VERSION = "2.1"

    def export_project_excel(
        self,
        options: ProjectExportExcelOptions,
        progress_callback: Optional[Callable[[str, int, int], None]] = None
    ) -> None:
        """Export complete project to Excel workbook with metadata.

        Creates .xlsx file with:
        - README sheet (human-readable overview)
        - Metadata sheets (result sets, load cases, stories, elements)
        - Result data sheets (one per result type)
        - IMPORT_DATA sheet (hidden JSON for re-import)
        """
        import pandas as pd
        from openpyxl import load_workbook
        from openpyxl.styles import Font, Alignment, PatternFill

        total_steps = 10
        current_step = 0

        # Step 1: Gather metadata
        if progress_callback:
            progress_callback("Gathering project metadata...", 1, total_steps)

        metadata = self._gather_project_metadata()
        current_step += 1

        # Step 2: Create Excel writer
        if progress_callback:
            progress_callback("Creating Excel workbook...", 2, total_steps)

        with pd.ExcelWriter(options.output_path, engine='openpyxl') as writer:
            # Step 3: Write README sheet
            if progress_callback:
                progress_callback("Writing README sheet...", 3, total_steps)
            self._write_readme_sheet(writer, metadata)
            current_step += 1

            # Step 4: Write metadata sheets
            if progress_callback:
                progress_callback("Writing metadata sheets...", 4, total_steps)
            self._write_metadata_sheets(writer, metadata)
            current_step += 1

            # Step 5-8: Write result data sheets
            if progress_callback:
                progress_callback("Writing result data sheets...", 5, total_steps)

            result_sheets = self._write_result_data_sheets(
                writer, metadata, options,
                lambda msg, curr, tot: progress_callback(msg, 5 + curr, total_steps) if progress_callback else None
            )
            current_step += 4

            # Step 9: Write IMPORT_DATA sheet
            if progress_callback:
                progress_callback("Writing import metadata...", 9, total_steps)
            self._write_import_data_sheet(writer, metadata, result_sheets)
            current_step += 1

        # Step 10: Apply formatting (reopen with openpyxl)
        if progress_callback:
            progress_callback("Applying formatting...", 10, total_steps)
        self._apply_excel_formatting(options.output_path)

        if progress_callback:
            progress_callback("Export complete!", total_steps, total_steps)

    def _gather_project_metadata(self) -> dict:
        """Gather all project metadata for export."""
        from database.catalog_base import get_catalog_session
        from database.catalog_repository import CatalogProjectRepository
        from services.project_service import get_project_summary
        from database.models import ResultSet, LoadCase, Story, Element

        # Get catalog entry
        catalog_session = get_catalog_session()
        try:
            catalog_repo = CatalogProjectRepository(catalog_session)
            catalog_project = catalog_repo.get_by_slug(self.context.slug)
        finally:
            catalog_session.close()

        # Get project summary
        summary = get_project_summary(self.context)

        # Query project database
        with self.context.session() as session:
            # Result sets
            result_sets = session.query(ResultSet).filter(
                ResultSet.project_id == self.result_service.project_id
            ).all()

            # Load cases
            load_cases = session.query(LoadCase).filter(
                LoadCase.project_id == self.result_service.project_id
            ).all()

            # Stories
            stories = session.query(Story).filter(
                Story.project_id == self.result_service.project_id
            ).order_by(Story.sort_order).all()

            # Elements
            elements = session.query(Element).filter(
                Element.project_id == self.result_service.project_id
            ).order_by(Element.element_type, Element.name).all()

            return {
                'catalog_project': catalog_project,
                'summary': summary,
                'result_sets': result_sets,
                'load_cases': load_cases,
                'stories': stories,
                'elements': elements,
            }

    def _write_readme_sheet(self, writer, metadata: dict) -> None:
        """Write README sheet with project overview."""
        catalog = metadata['catalog_project']
        summary = metadata['summary']

        # Build README content
        readme_lines = [
            ["PROJECT INFORMATION"],
            ["==================="],
            [""],
            ["Project Name:", catalog.name],
            ["Description:", catalog.description or ""],
            ["Created:", catalog.created_at.strftime("%Y-%m-%d %H:%M:%S")],
            ["Exported:", datetime.now().strftime("%Y-%m-%d %H:%M:%S")],
            ["RPS Version:", self.APP_VERSION],
            [""],
            ["DATABASE SUMMARY"],
            ["================"],
            [""],
            ["Result Sets:", summary.result_sets],
            ["Load Cases:", summary.load_cases],
            ["Stories:", summary.stories],
            ["Elements:", len(metadata['elements'])],
            [""],
            ["IMPORT INSTRUCTIONS"],
            ["==================="],
            [""],
            ["To import this project into RPS:"],
            ["1. Open RPS application"],
            ["2. Click 'Import Project' on Projects page"],
            ["3. Select this Excel file"],
            ["4. Review project summary"],
            ["5. Click 'Import'"],
            [""],
            ["The hidden 'IMPORT_DATA' sheet contains metadata required for re-import."],
            ["Do NOT delete or modify this sheet."],
        ]

        df = pd.DataFrame(readme_lines)
        df.to_excel(writer, sheet_name="README", index=False, header=False)

    def _write_metadata_sheets(self, writer, metadata: dict) -> None:
        """Write metadata sheets (Result Sets, Load Cases, Stories, Elements)."""
        # Result Sets sheet
        result_sets_data = [
            {
                "Name": rs.name,
                "Description": rs.description or "",
                "Created At": rs.created_at.strftime("%Y-%m-%d %H:%M:%S") if rs.created_at else "",
            }
            for rs in metadata['result_sets']
        ]
        pd.DataFrame(result_sets_data).to_excel(writer, sheet_name="Result Sets", index=False)

        # Load Cases sheet
        load_cases_data = [
            {
                "Name": lc.name,
                "Description": lc.description or "",
            }
            for lc in metadata['load_cases']
        ]
        pd.DataFrame(load_cases_data).to_excel(writer, sheet_name="Load Cases", index=False)

        # Stories sheet
        stories_data = [
            {
                "Name": s.name,
                "Sort Order": s.sort_order,
                "Height": s.height or 0.0,
            }
            for s in metadata['stories']
        ]
        pd.DataFrame(stories_data).to_excel(writer, sheet_name="Stories", index=False)

        # Elements sheet
        elements_data = [
            {
                "Name": e.name,
                "Element Type": e.element_type,
                "Description": e.description or "",
            }
            for e in metadata['elements']
        ]
        pd.DataFrame(elements_data).to_excel(writer, sheet_name="Elements", index=False)

    def _write_result_data_sheets(
        self,
        writer,
        metadata: dict,
        options: ProjectExportExcelOptions,
        progress_callback: Optional[Callable] = None
    ) -> dict:
        """Write result data sheets (one per result type).

        Returns:
            Dict mapping result type to sheet name for IMPORT_DATA
        """
        result_sheets = {'global': [], 'element': []}

        # Determine which result sets to export
        if options.result_set_ids:
            result_sets = [rs for rs in metadata['result_sets'] if rs.id in options.result_set_ids]
        else:
            result_sets = metadata['result_sets']

        # For simplicity, export first result set only
        # (Multi-result-set export can be added later)
        if not result_sets:
            return result_sheets

        result_set = result_sets[0]

        # Discover available result types
        from database.models import GlobalResultsCache, ElementResultsCache

        with self.context.session() as session:
            # Global results
            global_types = session.query(GlobalResultsCache.result_type).filter(
                GlobalResultsCache.result_set_id == result_set.id
            ).distinct().all()

            for base_type, in global_types:
                # Expand to include directions
                from config.result_config import RESULT_CONFIGS
                for config_key, config in RESULT_CONFIGS.items():
                    if config.name == base_type and config_key in RESULT_CONFIGS:
                        # Get dataset
                        direction = self._extract_direction(config_key, config)
                        base = self._extract_base_type(config_key)

                        dataset = self.result_service.get_standard_dataset(
                            result_type=base,
                            direction=direction,
                            result_set_id=result_set.id
                        )

                        if dataset and dataset.data is not None and not dataset.data.empty:
                            # Write to sheet
                            sheet_name = config_key[:31]  # Excel 31-char limit
                            dataset.data.to_excel(writer, sheet_name=sheet_name, index=False)
                            result_sheets['global'].append(config_key)

                            if progress_callback:
                                progress_callback(f"Exported {config_key}", 0, 1)

            # Element results
            element_types = session.query(ElementResultsCache.result_type).filter(
                ElementResultsCache.result_set_id == result_set.id
            ).distinct().all()

            for result_type, in element_types:
                # Get combined element data
                df = self.get_element_export_dataframe(result_type, result_set.id)

                if df is not None and not df.empty:
                    sheet_name = result_type[:31]
                    df.to_excel(writer, sheet_name=sheet_name, index=False)
                    result_sheets['element'].append(result_type)

                    if progress_callback:
                        progress_callback(f"Exported {result_type}", 0, 1)

        return result_sheets

    def _write_import_data_sheet(self, writer, metadata: dict, result_sheets: dict) -> None:
        """Write IMPORT_DATA sheet with JSON metadata."""
        import json

        # Build import metadata
        import_data = {
            "version": self.APP_VERSION,
            "export_timestamp": datetime.now().isoformat(),
            "project": {
                "name": metadata['catalog_project'].name,
                "slug": metadata['catalog_project'].slug,
                "description": metadata['catalog_project'].description or "",
                "created_at": metadata['catalog_project'].created_at.isoformat(),
            },
            "result_sets": [
                {
                    "name": rs.name,
                    "description": rs.description or "",
                    "created_at": rs.created_at.isoformat() if rs.created_at else None,
                }
                for rs in metadata['result_sets']
            ],
            "load_cases": [
                {"name": lc.name, "description": lc.description or ""}
                for lc in metadata['load_cases']
            ],
            "stories": [
                {"name": s.name, "sort_order": s.sort_order, "height": s.height or 0.0}
                for s in metadata['stories']
            ],
            "elements": [
                {"name": e.name, "element_type": e.element_type, "description": e.description or ""}
                for e in metadata['elements']
            ],
            "result_sheet_mapping": result_sheets,
        }

        # Write as single-cell JSON
        json_str = json.dumps(import_data, indent=2)
        df = pd.DataFrame([[json_str]], columns=["import_metadata"])
        df.to_excel(writer, sheet_name="IMPORT_DATA", index=False)

    def _apply_excel_formatting(self, file_path: Path) -> None:
        """Apply formatting to Excel workbook (bold headers, hide IMPORT_DATA sheet)."""
        from openpyxl import load_workbook
        from openpyxl.styles import Font, Alignment

        wb = load_workbook(file_path)

        # Format README sheet
        if "README" in wb.sheetnames:
            ws = wb["README"]
            for row in ws.iter_rows(min_row=1, max_row=1):
                for cell in row:
                    cell.font = Font(bold=True, size=14)

        # Hide IMPORT_DATA sheet
        if "IMPORT_DATA" in wb.sheetnames:
            wb["IMPORT_DATA"].sheet_state = "hidden"

        wb.save(file_path)
```

---

### 1.2 Export Project Dialog

**File**: `src/gui/export_dialog.py` (add ExportProjectExcelDialog class)

```python
class ExportProjectExcelDialog(QDialog):
    """Dialog for exporting project to Excel workbook."""

    def __init__(self, context: ProjectContext, result_service, project_name: str, parent=None):
        super().__init__(parent)
        self.context = context
        self.result_service = result_service
        self.project_name = project_name

        self.setWindowTitle("Export Project to Excel")
        self.setMinimumWidth(650)
        self._setup_ui()
        self._apply_styling()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        layout.setContentsMargins(24, 24, 24, 24)

        # Header
        header = QLabel(f"Export Project: {self.project_name}")
        header.setStyleSheet(f"font-size: 16px; font-weight: 600; color: {COLORS['text']};")
        layout.addWidget(header)

        # Info
        info = QLabel(
            "Export complete project as Excel workbook (.xlsx) with:\n"
            "• Human-readable sheets (README, metadata, result data)\n"
            "• Import metadata for re-importing into RPS\n"
            "• Open in Excel for inspection/analysis"
        )
        info.setWordWrap(True)
        info.setStyleSheet(f"color: {COLORS['muted']}; font-size: 13px;")
        layout.addWidget(info)

        # Export options
        options_group = QGroupBox("Export Options")
        options_layout = QVBoxLayout()

        self.include_all_check = QCheckBox("Include all result types")
        self.include_all_check.setChecked(True)
        self.include_all_check.setToolTip("Export all available result data")
        options_layout.addWidget(self.include_all_check)

        options_group.setLayout(options_layout)
        layout.addWidget(options_group)

        # Output file
        file_group = QGroupBox("Output File")
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

        # Progress
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)

        self.status_label = QLabel("")
        self.status_label.setStyleSheet(f"color: {COLORS['muted']}; font-size: 13px;")
        self.status_label.setVisible(False)
        layout.addWidget(self.status_label)

        # Buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        export_btn = create_styled_button("Export to Excel", "primary", "md")
        export_btn.clicked.connect(self._start_export)
        button_layout.addWidget(export_btn)

        cancel_btn = create_styled_button("Cancel", "secondary", "md")
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)

        layout.addLayout(button_layout)

    def _browse_file(self):
        suggested_name = f"{self.project_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"

        file_path, _ = QFileDialog.getSaveFileName(
            self, "Save Project Export",
            str(Path.home() / suggested_name),
            "Excel Files (*.xlsx)",
        )

        if file_path:
            self.file_path_edit.setText(file_path)
            self._update_empty_state()

    def _update_empty_state(self):
        is_empty = not self.file_path_edit.text().strip()
        self.file_path_edit.setProperty("empty", "true" if is_empty else "false")
        self.file_path_edit.style().unpolish(self.file_path_edit)
        self.file_path_edit.style().polish(self.file_path_edit)

    def _start_export(self):
        if not self.file_path_edit.text().strip():
            QMessageBox.warning(self, "Export Error", "Please select an output file.")
            return

        from services.export_service import ProjectExportExcelOptions

        options = ProjectExportExcelOptions(
            output_path=Path(self.file_path_edit.text()),
            include_all_results=self.include_all_check.isChecked()
        )

        self.progress_bar.setVisible(True)
        self.status_label.setVisible(True)

        self.worker = ExportProjectExcelWorker(self.context, self.result_service, options)
        self.worker.progress.connect(self._on_progress)
        self.worker.finished.connect(self._on_finished)
        self.worker.start()

    def _on_progress(self, message: str, current: int, total: int):
        self.progress_bar.setMaximum(total)
        self.progress_bar.setValue(current)
        self.status_label.setText(message)

    def _on_finished(self, success: bool, message: str, output_path: str):
        self.progress_bar.setVisible(False)
        self.status_label.setVisible(False)

        if success:
            QMessageBox.information(
                self, "Export Complete",
                f"{message}\n\nSaved to:\n{output_path}\n\nYou can now open this file in Excel."
            )
            self.accept()
        else:
            QMessageBox.critical(self, "Export Failed", message)

    def _apply_styling(self):
        # ... (same as other dialogs)


class ExportProjectExcelWorker(QThread):
    """Background worker for Excel project export."""

    progress = pyqtSignal(str, int, int)
    finished = pyqtSignal(bool, str, str)

    def __init__(self, context, result_service, options):
        super().__init__()
        self.context = context
        self.result_service = result_service
        self.options = options

    def run(self):
        try:
            from services.export_service import ExportService

            export_service = ExportService(self.context, self.result_service)

            export_service.export_project_excel(
                self.options,
                progress_callback=self._emit_progress
            )

            self.finished.emit(
                True,
                "Project exported successfully to Excel!",
                str(self.options.output_path)
            )
        except Exception as e:
            import traceback
            traceback.print_exc()
            self.finished.emit(False, f"Export failed: {str(e)}", "")

    def _emit_progress(self, message: str, current: int, total: int):
        self.progress.emit(message, current, total)
```

---

## Phase 2: Import Project from Excel (8 hours)

### 2.1 Import Service

**File**: `src/services/import_service.py` (new, ~400 lines)

```python
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
        """
        warnings = []
        can_import = True

        try:
            # Read IMPORT_DATA sheet
            import_data_df = pd.read_excel(excel_path, sheet_name="IMPORT_DATA")
            import_metadata = json.loads(import_data_df.iloc[0, 0])

            project_info = import_metadata.get('project', {})
            result_sheets = import_metadata.get('result_sheet_mapping', {})

            # Validate required sheets exist
            xl_file = pd.ExcelFile(excel_path)
            required_sheets = ["README", "Result Sets", "Load Cases", "Stories", "Elements", "IMPORT_DATA"]
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

        Returns:
            ProjectContext for newly imported project
        """
        total_steps = 8

        # Step 1: Read import metadata
        if progress_callback:
            progress_callback("Reading import metadata...", 1, total_steps)

        import_data_df = pd.read_excel(options.excel_path, sheet_name="IMPORT_DATA")
        import_metadata = json.loads(import_data_df.iloc[0, 0])

        project_info = import_metadata.get('project', {})
        project_name = options.new_project_name or project_info.get('name')

        # Step 2: Create/ensure project context
        if progress_callback:
            progress_callback("Creating project...", 2, total_steps)

        context = ensure_project_context(
            name=project_name,
            description=project_info.get('description', '')
        )

        # Step 3: Import metadata (result sets, load cases, stories, elements)
        if progress_callback:
            progress_callback("Importing metadata...", 3, total_steps)

        self._import_metadata(context, import_metadata)

        # Step 4-7: Import result data
        if progress_callback:
            progress_callback("Importing result data...", 4, total_steps)

        self._import_result_data(
            context, options.excel_path, import_metadata,
            lambda msg, curr, tot: progress_callback(msg, 4 + curr, total_steps) if progress_callback else None
        )

        # Step 8: Complete
        if progress_callback:
            progress_callback("Import complete!", total_steps, total_steps)

        return context

    def _import_metadata(self, context: ProjectContext, import_metadata: dict) -> None:
        """Import metadata tables (result sets, load cases, stories, elements)."""
        with context.session() as session:
            project_repo = ProjectRepository(session)
            project = project_repo.get_by_name(context.name)

            if not project:
                raise ValueError(f"Project '{context.name}' not found in database")

            # Import result sets
            result_set_repo = ResultSetRepository(session)
            result_set_mapping = {}
            for rs_data in import_metadata.get('result_sets', []):
                rs = result_set_repo.create(
                    project_id=project.id,
                    name=rs_data['name'],
                    description=rs_data.get('description', '')
                )
                result_set_mapping[rs_data['name']] = rs.id

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
                    height=s_data.get('height', 0.0)
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
                    description=e_data.get('description', '')
                )
                element_mapping[e_data['name']] = e.id

            session.commit()

            # Store mappings for result data import
            self._import_context = {
                'project_id': project.id,
                'result_set_mapping': result_set_mapping,
                'load_case_mapping': load_case_mapping,
                'story_mapping': story_mapping,
                'element_mapping': element_mapping,
            }

    def _import_result_data(
        self,
        context: ProjectContext,
        excel_path: Path,
        import_metadata: dict,
        progress_callback: Optional[Callable] = None
    ) -> None:
        """Import result data from Excel sheets into cache tables."""
        result_sheets = import_metadata.get('result_sheet_mapping', {})
        global_types = result_sheets.get('global', [])
        element_types = result_sheets.get('element', [])

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
                df = pd.read_excel(excel_path, sheet_name=sheet_name)

                # Parse DataFrame and write to GlobalResultsCache
                self._import_global_result(session, cache_repo, result_type, df)
                current += 1

            # Import element results
            for result_type in element_types:
                if progress_callback:
                    progress_callback(f"Importing {result_type}...", current, total)

                sheet_name = result_type[:31]
                df = pd.read_excel(excel_path, sheet_name=sheet_name)

                # Parse DataFrame and write to ElementResultsCache
                self._import_element_result(session, element_cache_repo, result_type, df)
                current += 1

            session.commit()

    def _import_global_result(self, session, cache_repo, result_type: str, df: pd.DataFrame) -> None:
        """Import global result data into GlobalResultsCache."""
        from database.models import GlobalResultsCache

        # Assume first result set (can be enhanced for multi-result-set)
        result_set_id = list(self._import_context['result_set_mapping'].values())[0]
        story_mapping = self._import_context['story_mapping']
        project_id = self._import_context['project_id']

        # Extract base type and direction
        from config.result_config import RESULT_CONFIGS
        config = RESULT_CONFIGS.get(result_type)
        if not config:
            print(f"Warning: Unknown result type {result_type}, skipping")
            return

        base_type = result_type.split('_')[0]  # "Drifts_X" -> "Drifts"

        # Process each story row
        for idx, row in df.iterrows():
            story_name = row['Story']
            story_id = story_mapping.get(story_name)

            if not story_id:
                continue

            # Build results_matrix (load case columns)
            results_matrix = {}
            for col in df.columns:
                if col != 'Story':
                    results_matrix[col] = row[col]

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

    def _import_element_result(self, session, element_cache_repo, result_type: str, df: pd.DataFrame) -> None:
        """Import element result data into ElementResultsCache."""
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
                    results_matrix[col] = row[col]

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
```

---

### 2.2 Import Project Dialog

**File**: `src/gui/import_dialog.py` (new, ~400 lines)

```python
"""Import dialog for RPS projects."""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QGroupBox,
    QFileDialog, QMessageBox, QProgressBar, QTextEdit
)
from PyQt6.QtCore import QThread, pyqtSignal
from pathlib import Path

from gui.ui_helpers import create_styled_button
from gui.styles import COLORS
from services.import_service import ImportService, ImportProjectExcelOptions


class ImportProjectDialog(QDialog):
    """Dialog for importing Excel project files."""

    def __init__(self, parent=None):
        super().__init__(parent)

        self.excel_path = None
        self.import_preview = None

        self.setWindowTitle("Import Project from Excel")
        self.setMinimumWidth(700)
        self.setMinimumHeight(600)

        self._setup_ui()
        self._apply_styling()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        layout.setContentsMargins(24, 24, 24, 24)

        # Header
        header = QLabel("Import Project from Excel")
        header.setStyleSheet(f"font-size: 16px; font-weight: 600; color: {COLORS['text']};")
        layout.addWidget(header)

        # File selection
        file_group = QGroupBox("Select Excel File")
        file_layout = QHBoxLayout()

        self.file_label = QLabel("No file selected")
        self.file_label.setStyleSheet(f"color: {COLORS['muted']};")
        file_layout.addWidget(self.file_label)

        browse_btn = create_styled_button("Browse...", "secondary", "sm")
        browse_btn.clicked.connect(self._browse_file)
        file_layout.addWidget(browse_btn)

        file_group.setLayout(file_layout)
        layout.addWidget(file_group)

        # Preview
        preview_group = QGroupBox("Project Preview")
        preview_layout = QVBoxLayout()

        self.preview_text = QTextEdit()
        self.preview_text.setReadOnly(True)
        self.preview_text.setMaximumHeight(300)
        self.preview_text.setPlainText("Select an Excel file to preview project details...")
        preview_layout.addWidget(self.preview_text)

        preview_group.setLayout(preview_layout)
        layout.addWidget(preview_group)

        # Progress
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)

        self.status_label = QLabel("")
        self.status_label.setStyleSheet(f"color: {COLORS['muted']}; font-size: 13px;")
        self.status_label.setVisible(False)
        layout.addWidget(self.status_label)

        # Buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        self.import_btn = create_styled_button("Import Project", "primary", "md")
        self.import_btn.setEnabled(False)
        self.import_btn.clicked.connect(self._start_import)
        button_layout.addWidget(self.import_btn)

        cancel_btn = create_styled_button("Cancel", "secondary", "md")
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)

        layout.addLayout(button_layout)

    def _browse_file(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Excel Project File",
            str(Path.home()),
            "Excel Files (*.xlsx)"
        )

        if file_path:
            self.excel_path = Path(file_path)
            self.file_label.setText(self.excel_path.name)
            self._preview_file()

    def _preview_file(self):
        """Preview Excel file before importing."""
        try:
            import_service = ImportService()
            self.import_preview = import_service.preview_import(self.excel_path)

            # Build preview text
            preview_lines = [
                f"Project Name: {self.import_preview.project_name}",
                f"Description: {self.import_preview.description}",
                "",
                f"Created: {self.import_preview.created_at}",
                f"Exported: {self.import_preview.exported_at}",
                "",
                "Database Summary:",
                f"  Result Sets: {self.import_preview.result_sets_count}",
                f"  Load Cases: {self.import_preview.load_cases_count}",
                f"  Stories: {self.import_preview.stories_count}",
                f"  Elements: {self.import_preview.elements_count}",
                "",
                f"Result Types ({len(self.import_preview.result_types)}):",
            ]

            for rt in self.import_preview.result_types:
                preview_lines.append(f"  • {rt}")

            if self.import_preview.warnings:
                preview_lines.append("")
                preview_lines.append("⚠ Warnings:")
                for warning in self.import_preview.warnings:
                    preview_lines.append(f"  • {warning}")

            self.preview_text.setPlainText("\n".join(preview_lines))

            # Enable import button if valid
            self.import_btn.setEnabled(self.import_preview.can_import)

        except Exception as e:
            self.preview_text.setPlainText(f"Error reading file:\n{str(e)}")
            self.import_btn.setEnabled(False)

    def _start_import(self):
        """Start import process."""
        if not self.excel_path or not self.import_preview:
            return

        # Confirm import
        reply = QMessageBox.question(
            self,
            "Confirm Import",
            f"Import project '{self.import_preview.project_name}'?\n\n"
            f"This will create a new project in RPS.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply != QMessageBox.StandardButton.Yes:
            return

        options = ImportProjectExcelOptions(excel_path=self.excel_path)

        self.progress_bar.setVisible(True)
        self.status_label.setVisible(True)
        self.import_btn.setEnabled(False)

        self.worker = ImportProjectWorker(options)
        self.worker.progress.connect(self._on_progress)
        self.worker.finished.connect(self._on_finished)
        self.worker.start()

    def _on_progress(self, message: str, current: int, total: int):
        self.progress_bar.setMaximum(total)
        self.progress_bar.setValue(current)
        self.status_label.setText(message)

    def _on_finished(self, success: bool, message: str):
        self.progress_bar.setVisible(False)
        self.status_label.setVisible(False)
        self.import_btn.setEnabled(True)

        if success:
            QMessageBox.information(
                self,
                "Import Complete",
                f"{message}\n\nProject has been imported successfully!"
            )
            self.accept()
        else:
            QMessageBox.critical(self, "Import Failed", message)

    def _apply_styling(self):
        self.setStyleSheet(f"""
            QGroupBox {{
                font-size: 14px;
                font-weight: 600;
                color: {COLORS['text']};
                border: 1px solid {COLORS['border']};
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
            QTextEdit {{
                background-color: {COLORS['card']};
                border: 1px solid {COLORS['border']};
                border-radius: 4px;
                color: {COLORS['text']};
                font-size: 13px;
                font-family: 'Courier New', monospace;
                padding: 8px;
            }}
            QProgressBar {{
                border: 1px solid {COLORS['border']};
                border-radius: 4px;
                background-color: {COLORS['card']};
                text-align: center;
                color: {COLORS['text']};
            }}
            QProgressBar::chunk {{
                background-color: {COLORS['accent']};
                border-radius: 3px;
            }}
        """)


class ImportProjectWorker(QThread):
    """Background worker for project import."""

    progress = pyqtSignal(str, int, int)
    finished = pyqtSignal(bool, str)

    def __init__(self, options: ImportProjectExcelOptions):
        super().__init__()
        self.options = options

    def run(self):
        try:
            import_service = ImportService()

            context = import_service.import_project_excel(
                self.options,
                progress_callback=self._emit_progress
            )

            self.finished.emit(
                True,
                f"Project '{context.name}' imported successfully!"
            )
        except Exception as e:
            import traceback
            traceback.print_exc()
            self.finished.emit(False, f"Import failed: {str(e)}")

    def _emit_progress(self, message: str, current: int, total: int):
        self.progress.emit(message, current, total)
```

---

### 2.3 Integration Points

**File**: `src/gui/project_detail_window.py` (add Export Project button)

```python
# After line ~160 (in toolbar)
export_project_btn = create_styled_button("Export Project", "secondary", "sm")
export_project_btn.setToolTip("Export project to Excel workbook")
export_project_btn.clicked.connect(self.export_project_excel)
toolbar_layout.addWidget(export_project_btn)

# Add method
def export_project_excel(self):
    """Export project to Excel workbook."""
    from gui.export_dialog import ExportProjectExcelDialog

    dialog = ExportProjectExcelDialog(
        context=self.context,
        result_service=self.result_service,
        project_name=self.project_name,
        parent=self
    )

    if dialog.exec():
        self.statusBar().showMessage("Project exported to Excel successfully!", 3000)
```

**File**: `src/gui/main_window.py` (add Import Project button)

```python
# Add to toolbar/menu
import_project_btn = create_styled_button("Import Project", "primary", "md")
import_project_btn.setToolTip("Import project from Excel file")
import_project_btn.clicked.connect(self.import_project)
toolbar_layout.addWidget(import_project_btn)

# Add method
def import_project(self):
    """Open import project dialog."""
    from gui.import_dialog import ImportProjectDialog

    dialog = ImportProjectDialog(parent=self)

    if dialog.exec():
        # Refresh project list
        self.load_projects()
        self.statusBar().showMessage("Project imported successfully!", 3000)
```

---

## Implementation Timeline

### Sprint 1: Export Project to Excel (2 days - 12 hours)

**Day 1 (6 hours)**:
1. Hours 1-3: Implement `ExportService.export_project_excel()`
   - Metadata gathering
   - README sheet writer
   - Metadata sheets (Result Sets, Load Cases, Stories, Elements)

2. Hours 4-6: Complete export logic
   - Result data sheets writer
   - IMPORT_DATA sheet with JSON
   - Excel formatting

**Day 2 (6 hours)**:
3. Hours 7-9: Create `ExportProjectExcelDialog` UI
   - File picker
   - Progress bar + worker
   - Integration with `ProjectDetailWindow`

4. Hours 10-12: Testing + Polish
   - Test with real project
   - Verify Excel output (open in Excel)
   - Bug fixes

### Sprint 2: Import Project from Excel (2 days - 12 hours)

**Day 3 (6 hours)**:
5. Hours 13-15: Implement `ImportService`
   - Preview functionality
   - Metadata import
   - Result data import

6. Hours 16-18: Complete import logic
   - Global results cache population
   - Element results cache population
   - Error handling

**Day 4 (6 hours)**:
7. Hours 19-21: Create `ImportProjectDialog` UI
   - File picker
   - Preview pane
   - Progress bar + worker
   - Integration with `MainWindow`

8. Hours 22-24: Round-trip testing
   - Export → Import → Verify
   - Test with multiple projects
   - Documentation

**Total Effort**: ~24 hours (3 developer days)

---

## Success Criteria

✅ Export creates valid Excel workbook with all sheets
✅ README sheet human-readable and informative
✅ Result data sheets match original table format
✅ IMPORT_DATA sheet contains complete JSON metadata
✅ Excel file can be opened and inspected in Microsoft Excel
✅ Import preview shows accurate project summary
✅ Import creates functional project identical to original
✅ Round-trip export → import preserves all data
✅ Progress bars update during long operations
✅ Error handling for corrupted/invalid Excel files
✅ Documentation updated

---

## Files Summary

**New Files (2)**:
1. `src/services/import_service.py` (~400 lines)
2. `src/gui/import_dialog.py` (~400 lines)
3. `docs/implementation/EXPORT_IMPORT_EXCEL_PLAN.md` (this file)

**Modified Files (3)**:
1. `src/services/export_service.py` (+300 lines)
2. `src/gui/export_dialog.py` (+250 lines - ExportProjectExcelDialog)
3. `src/gui/project_detail_window.py` (+20 lines)
4. `src/gui/main_window.py` (+20 lines)

**Total New Code**: ~1,400 lines
**Test Coverage**: Import/export round-trip tests

---

This approach gives you:
1. **Human-readable format** - Open in Excel for inspection
2. **Re-import capability** - Full project restoration
3. **Collaboration-friendly** - Share via email/cloud storage
4. **Manual editing** - Modify results if needed
5. **No binary formats** - Standard Excel `.xlsx`

Ready to implement?
