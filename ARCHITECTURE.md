# RPS Architecture (Condensed)

**Version**: 2.8 | **Date**: 2024-11-15

> **Full details in code comments and docstrings. This doc covers key patterns only.**

---

## 1. System Overview

**RPS** = Results Processing System for structural engineering (ETABS/SAP2000)

**Stack**: PyQt6 (UI) + PyQtGraph (plots) + SQLite (data) + SQLAlchemy (ORM) + Pandas (processing)

**Architecture**: Layered (UI → Service → Repository → Database)

**New in v2.8**: Import system refactored with service layer extraction, provider pattern for data retrieval, and repository separation for cleaner architecture. Import prescan logic moved to dedicated service with parallel execution. Data providers handle caching independently. Element queries extracted to specialized repository.

---

## 2. Data Model (24 Tables)

### Catalog Database (`data/catalog.db`)
- `catalog_projects` - Project metadata + DB paths

### Per-Project Database (`data/projects/{slug}/{slug}.db`)

**Core** (6 tables):
- `projects`, `stories`, `load_cases`, `result_sets`, `comparison_sets`, `elements`

**Global Results** (4 tables):
- `story_drifts`, `story_accelerations`, `story_forces`, `story_displacements`

**Element Results** (6 tables):
- `wall_shears`, `quad_rotations`, `column_shears`, `column_axials`, `column_rotations`, `beam_rotations`

**Foundation Results** (2 tables):
- `soil_pressures` - Minimum soil pressure per foundation element/load case
- `vertical_displacements` - Minimum vertical displacement (Uz) per foundation joint/load case

**Cache** (4 tables):
- `global_results_cache` - Wide format for fast querying (story-based)
- `element_results_cache` - Wide format for elements
- `joint_results_cache` - Wide format for foundation/joint results (NEW in v2.5)
- `absolute_maxmin_drifts` - Pre-computed max/min envelopes

**Future** (2 tables):
- `time_history_data`, `result_categories`

### ComparisonSet Model
**Purpose**: Store configurations for comparing multiple result sets

**Fields**:
- `id` - Primary key
- `project_id` - Foreign key to projects
- `name` - Comparison set name (e.g., 'COM1', 'COM2')
- `description` - Optional description
- `result_set_ids` - JSON array of result set IDs to compare
- `result_types` - JSON array of result types to include
- `created_at` - Timestamp

**Usage**:
- Browser shows comparison sets (COM1, COM2) alongside regular result sets
- **Global results**: Click "Drifts X" → shows averaged data for all result sets (story-based)
- **Element results**: Expand "Walls → Shears → P1 → V2" → shows P1's V2 shear across all result sets (story-based)
- **Joint results**: Expand "Joints → Soil Pressures → F1" → shows F1's soil pressures across all result sets (load case-based)
- Data displayed in custom comparison view with ratio analysis

### Foundation Results Models

**SoilPressure**:
- Stores minimum soil pressure per foundation element
- Fields: `unique_name`, `shell_object`, `load_case_id`, `min_pressure`
- Cache: `JointResultsCache` with `result_type='SoilPressures_Min'`

**VerticalDisplacement**:
- Stores minimum vertical displacement (Uz) for foundation joints
- Fields: `unique_name`, `label`, `story`, `load_case_id`, `min_displacement`
- Filtered by joints from "Fou" sheet during import
- Cache: `JointResultsCache` with `result_type='VerticalDisplacements_Min'`

**Key Differences from Story-Based Results**:
- No story relationship (foundation is single-level)
- Grouped by unique_name instead of story_id
- Summary columns (Avg/Max/Min) calculated across load cases
- Comparisons organized by load case (not by story)

### Key Fields
- **Story ordering**: `sort_order` (global), `story_sort_order` (per-result)
- **Element type**: `element_type` in ('Wall', 'Quad', 'Column', 'Beam')
- **Cache columns**: JSON-serialized load case columns for dynamic querying

---

## 3. Configuration System

### Result Type Configuration (`config/result_config.py`)
```python
RESULT_CONFIGS = {
    'Drifts_X': ResultTypeConfig(
        name='Drifts', direction='X', unit='%',
        color_scheme='blue_orange', decimal_places=3,
        category='Envelopes', subcategory='Story',
        display_name='Story Drifts (X)'
    )
}
```

**Adding new type**:
1. Add config to `RESULT_CONFIGS`
2. Create transformer in `processing/result_transformers.py`
3. Register in `TRANSFORMERS` dict
4. Done! UI, colors, formatting auto-configured

**Color Schemes** (`utils/color_utils.py`):
- `blue_orange`: Blue (low) → Orange (high) - Default for most results
- `orange_blue`: Orange (low) → Blue (high) - Used for foundation results where lower values are critical
- `green_red`: Green → Red
- `cool_warm`: Cool blue → Warm red
- `teal_yellow`: Teal → Yellow

**Foundation Result Configuration** (v2.5):
- `SoilPressures_Min`: Uses `orange_blue` scheme (lower pressure = orange = critical)
- `VerticalDisplacements_Min`: Uses `orange_blue` scheme (lower displacement = orange = critical)
- Both include Average, Maximum, Minimum summary columns

---

## 4. Key Patterns

### Repository Pattern (v2.8 Refactor)

**Base Repository** (`database/base_repository.py`):
```python
class BaseRepository(Generic[ModelT]):
    model: Type[ModelT]

    def get_by_id(self, id: int) -> Optional[ModelT]:
        return self.session.query(self.model).filter(...).first()

    def create(self, **kwargs) -> ModelT:
        obj = self.model(**kwargs)
        self.session.add(obj)
        self.session.commit()
        return obj

    # delete(), list_all() also provided
```

**Domain Repositories** (`database/repository.py`):
```python
class StoryRepository(BaseRepository[Story]):
    model = Story

    def get_by_name(self, name: str) -> Optional[Story]:
        return self.session.query(self.model).filter(...).first()
```

**Specialized Query Repositories** (`database/element_result_repository.py`):
- `ElementResultQueryRepository` - Complex queries for element max/min datasets
  - Model registry pattern: Maps result type to (model, max_attr, min_attr, direction_attr, multiplier)
  - Supports: WallShears, ColumnShears, ColumnRotations, BeamRotations, QuadRotations
  - `fetch_records()` - Joins with LoadCase and Story, filters by element_id
  - Returns model info for dynamic attribute access

**Separation of Concerns**:
- `BaseRepository` - Generic CRUD operations
- Domain repositories (e.g., `StoryRepository`) - Domain-specific queries
- Specialized repositories (e.g., `ElementResultQueryRepository`) - Complex aggregation queries

### Transformer Pattern
**Converts Excel data → Database models**:
```python
class DriftTransformer(BaseTransformer):
    def transform(self, df: pd.DataFrame, ...) -> List[StoryDrift]:
        # Parse DataFrame, create model objects
        return drift_objects
```

**Registration**: `TRANSFORMERS['Drifts_X'] = DriftTransformer()`

### Service Layer
**`ResultDataService`** - Main data retrieval facade (cached):
- `get_standard_dataset()` - Global results (table + plot data)
- `get_element_dataset()` - Element results
- `get_joint_dataset()` - Foundation/joint results
- `get_maxmin_dataset()` - Max/Min envelopes
- `get_comparison_dataset()` - Comparison results (global, element, or joint)

**Provider Pattern** (`providers.py`):
- `StandardDatasetProvider` - Global/story-based results with per-dataset caching
- `ElementDatasetProvider` - Element-specific results with per-dataset caching
- `JointDatasetProvider` - Foundation/joint results with per-dataset caching
- Each provider manages its own cache dictionary and invalidation
- Providers instantiated once per `ResultDataService` instance

**Modular structure** (7 files in `processing/result_service/`):
- `service.py` - Facade with provider-based architecture
- `providers.py` - Dataset providers (Standard, Element, Joint)
- `cache_builder.py` - Dataset construction logic
- `maxmin_builder.py` - Max/Min envelope calculations
- `comparison_builder.py` - Comparison logic (global, element & joint)
- `models.py` - ResultDataset, MaxMinDataset, ComparisonDataset
- `metadata.py` - Display label generation
- `story_loader.py` - Story data caching

**Comparison Builder**:
- `build_global_comparison()` - Compare global results across result sets
- `build_element_comparison()` - Compare specific element across result sets
- `build_joint_comparison()` - Compare foundation results across result sets
- Aggregates averaged data from multiple result sets
- Calculates ratio columns (last/first result set)

---

## 5. Import Flow

### Standard Import
1. User selects folder → `FolderImportDialog`
2. Scan files → discover load cases → `LoadCaseScanWorker`
3. User selects cases → resolve conflicts → `LoadCaseConflictDialog`
4. Import → `EnhancedFolderImporter`
   - Parses Excel → `ExcelParser`
   - Transforms data → `TRANSFORMERS[type]`
   - Saves to DB → `Repository.bulk_create()`
5. Build cache → `DataImporter._build_cache()`

### Foundation Import (v2.5)
**Vertical Displacements**:
1. Pre-scan phase: Collect foundation joints from **any** file with "Fou" sheet
2. Foundation joints shared across all files in batch
3. Import phase: Process "Joint Displacements" in **all** files
4. Filter by foundation joints from shared list
5. Cache with lexicographic load case ordering

**Soil Pressures**:
1. Pre-scan phase: Detect "Soil Pressures" sheet in each file
2. Import phase: Process all soil pressure data
3. Cache with lexicographic load case ordering

**Key Differences**:
- Foundation joints propagated across files (not per-file)
- Joint results stored in `JointResultsCache` (not story-based cache)
- Summary columns (Avg/Max/Min) calculated during dataset retrieval

### Import Service Architecture (v2.8 Refactor)

**Prescan Service** (`services/import_preparation.py`):
- `ImportPreparationService` - Headless service for folder/file scanning
  - `prescan_folder()` - Scan all Excel files in folder with parallel execution
  - `prescan_files()` - Scan specific list of files
  - `_extract_load_cases_from_sheet()` - Per-sheet load case extraction
  - Uses `ThreadPoolExecutor` with 6 workers for concurrent file scanning
- `PrescanResult` - Aggregated scan results (file_load_cases, foundation_joints, errors)
- `FilePrescanSummary` - Per-file summary (load_cases_by_sheet, available_sheets, foundation_joints)
- `detect_conflicts()` - Pure function for identifying conflicting load cases
- `determine_allowed_load_cases()` - Pure function for filtering based on resolution

**Import Hierarchy**:
- `BaseFolderImporter` - Session management + progress callbacks
- `EnhancedFolderImporter` - Enhanced import with conflict resolution
  - Accepts `prescan_result` parameter to avoid re-scanning
  - Uses `ImportPreparationService` internally
  - Delegates to `SelectiveDataImporter` for actual import
- `DataImporter` - Single-file import with cache building
- `SelectiveDataImporter` - Filtered import with load case selection

**Key Components**:
- `ExcelParser` - Sheet parsing (supports all result types including foundation)
- `ResultTransformers` - Excel → ORM model conversion
- `PhaseTimer` - Import phase instrumentation for performance monitoring
- `ResultProcessor` - Vectorized groupby/pivot for expensive transforms

---

## 6. Export Flow

### Export Results (v2.7 - Multi-Result-Set Support)
1. User clicks "Export Results" → `ComprehensiveExportDialog`
2. **Auto-discover**:
   - Query `GlobalResultsCache`, `ElementResultsCache`, `JointResultsCache`
   - Query all result sets in project
   - Show base types only (e.g., "Drifts", "SoilPressures")
3. **Dialog layout** (wide, 2-column):
   - Left (40%): Result Types tree (Global | Element | Joint)
   - Right (60%): Result Sets selector (all checked) + Export Options + Output
4. User selects:
   - Result sets to export (multiple allowed, all selected by default)
   - Result types to export (expand to directions on export)
   - Format (Excel/CSV) + combined/separate mode
5. **Export process** → `ComprehensiveExportWorker`
   - Generate **single timestamp** for entire operation
   - Iterate: `for result_set_id in selected_result_set_ids`
   - For each result type:
     - **Global**: Query with `get_standard_dataset(result_type, direction, result_set_id)`
     - **Element**: Query with `get_element_export_dataframe(result_type, result_set_id)`
     - **Joint**: Query with `get_joint_dataset(result_type + '_Min', result_set_id)`
   - Write files/sheets: `{result_set_name}_{result_type}_{timestamp}.xlsx`
6. **Type expansion**:
   - Global: `_get_selected_result_types()` finds all directional variants in RESULT_CONFIGS
   - Element: Query cache for `{base_type}_V2`, `{base_type}_V3` variants
   - Joint: Query cache for `{base_type}_Min` variants (then remove `_Min` from display)

**Key Features**:
- Multiple result sets exported in one operation
- Single timestamp ensures file grouping
- Joint results properly handle `_Min` suffix internally
- Sheet/file names use clean display names (no `_Min`)

### Export Project
1. User clicks "Export Project" → `ExportProjectExcelDialog`
2. Export all data → `ProjectExportService`
3. Create human-readable sheets + IMPORT_DATA (JSON)
4. Write .xlsx → Can be re-imported via `ImportProjectDialog`

---

## 7. UI Architecture

### Main Window (`main_window.py`)
- Project grid (cards) → click → `ProjectDetailWindow`

### Project Detail Window (`project_detail_window.py`)
**3-panel layout**:
- Browser (left 25%) - `ResultsTreeBrowser`
- Content (right 75%) - Dynamic widgets:
  - `StandardResultView` - Table + Plot (directional results)
  - `ComparisonResultView` - Multi-series comparison (table + plot with custom legend)
  - `MaxMinDriftsWidget` - Max/Min tables + plots
  - `AllRotationsWidget` - Scatter plot for all rotations
  - `BeamRotationsWidget` - Beam-specific view

**Browser hierarchy**:
```
Results
  ├─ DES (result set)
  │   └─ Global Results
  │       └─ Drifts
  │           ├─ X Direction → StandardResultView
  │           ├─ Y Direction → StandardResultView
  │           └─ Max/Min → MaxMinDriftsWidget
  │       └─ Forces, Accelerations, Displacements...
  │   └─ Elements
  │       └─ Walls
  │           └─ Shears
  │               └─ P1
  │                   ├─ V2 → StandardResultView
  │                   └─ V3 → StandardResultView
  ├─ MCE (result set)
  └─ COM1 (comparison set)
      ├─ Global
      │   └─ Drifts
      │       ├─ X Direction → ComparisonResultView
      │       └─ Y Direction → ComparisonResultView
      └─ Elements
          └─ Walls
              └─ Shears
                  └─ P1
                      ├─ V2 → ComparisonResultView (P1 across all result sets)
                      └─ V3 → ComparisonResultView (P1 across all result sets)
```

### Reusable Components
- `StandardResultView` - Auto-wires table ↔ plot signals
- `ComparisonResultView` - Multi-series comparison with custom plot widget
- `ResultsTableWidget` - Manual selection, gradient colors
- `ResultsPlotWidget` - PyQtGraph plots with tabs and legend interaction
- `ComparisonPlotWidget` - Single plot without tabs, vertical legend on right
- `create_styled_button()`, `create_styled_label()` - Design system helpers

### Comparison Feature (v2.7)

**Components**:
- `ComparisonSetDialog` - Dialog for creating comparisons (wide layout, filtered types)
- `ComparisonResultView` - Custom view with table and plot (no tabs)
- `ComparisonPlotWidget` - Dedicated plot widget with rounded card legend
- `ComparisonJointScatterWidget` - Scatter plot for joint result comparisons (NEW in v2.7)
- `comparison_builder.py` - Service layer for building comparison datasets (4 types)
- `ComparisonSet` model - Database persistence
- `BlurOverlay` - Transparent blur effect for modal dialogs (NEW in v2.7)

**Comparison Types**:
1. **Global Comparison** (`build_global_comparison`) - Story-based results
   - Result types: Drifts, Forces, Accelerations, Displacements
   - Organization: By Story
   - Example: "Story 5" drifts across DES, MCE, SLE

2. **Element Comparison** (`build_element_comparison`) - Element-specific results
   - Result types: WallShears, ColumnShears, BeamRotations
   - Organization: By Story for specific element
   - Example: "Wall P1 V2" shears across DES, MCE, SLE

3. **Joint Comparison** (`build_joint_comparison`) - Foundation/joint results (v2.5)
   - Result types: SoilPressures_Min, VerticalDisplacements_Min
   - Organization: By Load Case for specific joint/element
   - Example: "Foundation F1" pressures across DES, MCE, SLE

4. **All Joints Comparison** (`build_all_joints_comparison`) - Scatter plot view (NEW in v2.7)
   - Result types: SoilPressures_Min, VerticalDisplacements_Min
   - Organization: All joints shown as scatter plot
   - X-axis: Load Cases | Y-axis: Values
   - Multiple result sets overlaid with different colors

**Data Flow**:
1. User clicks "Create Comparison" → `ComparisonSetDialog` opens (wide layout)
   - **Dialog features** (v2.7):
     - Wide 1200x650 layout matching import dialog
     - Result type filtering: Only shows types available in project
     - 3-column result type display (Global | Element | Joint)
     - Blur overlay effect on parent window
2. Select ≥2 result sets (DES, MCE, SLE) and result types (Drifts, Forces, etc.)
3. Save to database → `ComparisonSet` created with JSON fields
4. Browser loads comparison sets alongside regular result sets
5. Click comparison node → `get_comparison_dataset()` fetches data
   - Global/Element: Calls `build_global_comparison()` or `build_element_comparison()`
   - Joint: Calls `build_joint_comparison()` with `unique_name` parameter
   - All Joints: Calls `build_all_joints_comparison()` for scatter view
6. Display options:
   - **ComparisonResultView** (table + plot):
     - Global/Element Table: Story | DES_Avg | MCE_Avg | MCE/DES (ratio)
     - Joint Table: Load Case | DES_Avg | MCE_Avg | MCE/DES (ratio)
     - Plot: Multi-series building profile with custom legend on right
   - **ComparisonJointScatterWidget** (scatter plot only):
     - All joints as scatter points with jitter
     - Load cases on X-axis, values on Y-axis
     - Each result set = different color
     - Vertical legend with rounded cards

**Comparison Table Features**:
- Centered values (Story/Load Case column left-aligned)
- Units only for drift results (%)
- Ratio column: Last/first result set (always 2 decimals, no unit)
- Dynamic width: Table sized to content, plot takes remaining space

**Comparison Plot Features**:
- Single plot (no tabs) - dedicated `ComparisonPlotWidget`
- Vertical legend on right with rounded card items
- Each card: colored square indicator + result set name
- Multi-series: Each result set = different color line
- Colors: Blue, Red, Green, Orange, Purple, Pink (cycling)

**Element Comparison Support**:
- Tree structure: COM1 → Elements → Walls → Shears → P1 → V2/V3
- Clicking element+direction shows that element across all result sets
- Title format: "P1 - WallShears V2 - DES vs MCE Comparison"
- Same table/plot structure as global comparisons
- Shared axes and scale
- NaN values handled gracefully (converted to 0 for plotting)

### Dialog UI Enhancements (v2.7)

**Blur Overlay System** (`blur_overlay.py`):
- Semi-transparent overlay with fade animations
- Applies to: Export, Comparison, Import dialogs
- Usage: `show_dialog_with_blur(dialog, parent_window)`
- Fade in: 200ms, Fade out: 200ms
- Opacity: 0.0 → 1.0 (black at 78% opacity)

**Wide Dialog Layout Pattern**:
All major dialogs now use consistent wide layout (1200+ width):

1. **Export Dialog** (1200x650+):
   - Left column (40%): Result Types tree (Global | Element | Joint)
   - Right column (60%): Result Sets + Export Options + Output (stacked)
   - Result Types: Full height, no scrolling needed
   - Result Sets: Compact 150px height
   - Custom checkboxes with checkmark images

2. **Comparison Dialog** (1200x650):
   - Left column (Result Sets to Compare)
   - Right column: 3-column result types display (Global | Element | Joint)
   - Result type filtering: Only available types shown
   - Background: Proper gray (`#0a0c10`)

3. **Import Dialog** (1200x650):
   - Left column: Files + load case selection
   - Right column: Import options + conflict resolution
   - Matching checkbox style across all dialogs

**Checkbox Styling** (consistent across dialogs):
- 18x18px indicators with rounded corners
- Hover state: Border color changes to accent
- Checked state: Accent background with white checkmark
- Checkmark: Custom PNG image generated with QPainter
- Stored in temp directory: `rps_export_checkbox_check.png`

---

## 8. Story Ordering System

**Problem**: Different Excel sheets have different story orders

**Solution**: Dual ordering system
- **Global**: `Story.sort_order` from "Story Drifts" sheet (0=bottom)
- **Per-Result**: `<result>.story_sort_order` from each sheet (0=first row)

**Display**:
- Plots: Bottom floors at y=0, top floors at y=max (ascending)
- Tables: Bottom floors first, top floors last (ascending)

**Exception**: Quad rotations always use global order (Excel sorted by element name, not height)

---

## 9. Design System (DESIGN.md)

**Colors**:
- Background: `#0a0c10`, Card: `#161b22`
- Accent: `#4a7d89` (teal), `#67e8f9` (cyan)
- Text: `#d1d5db`, Muted: `#9ca3af`

**Spacing**: 4px increments (4, 8, 12, 16, 24)

**Typography**: 14px base, 24px headers, 13px muted text

**Gradient Colors**: `blue_orange`, `green_red`, `purple_yellow`
- `get_gradient_color(value, min, max, scheme)` → QColor

---

## 10. Testing

**Unit Tests** (`tests/`):
- Stub pattern for database access
- Mock pattern for external dependencies
- Pytest fixtures for common setups

**Test Coverage**:
- Repository layer: CRUD operations
- Service layer: Dataset building
- Transformer layer: Excel → Model conversion

---

## 11. Migration & Deployment

**Database Migrations** (Alembic):
```bash
# Create migration
pipenv run alembic revision --autogenerate -m "Description"

# Apply migrations
pipenv run alembic upgrade head
```

**Building**:
```bash
# Create standalone .exe
pipenv run pyinstaller src/main.py --onefile --windowed --name RPS

# Output: dist/RPS.exe
```

**Deployment**:
- Portable .exe (no installation)
- SQLite databases in `data/` folder
- First run auto-creates schema

---

## 12. Extension Points

### Adding Result Types
1. Config: `RESULT_CONFIGS['NewType'] = ResultTypeConfig(...)`
2. Transformer: `class NewTypeTransformer(BaseTransformer): ...`
3. Register: `TRANSFORMERS['NewType'] = NewTypeTransformer()`

### Adding UI Views
1. Create widget extending `QWidget`
2. Add to `ProjectDetailWindow._setup_content_area()`
3. Wire signals: `browser.selection_changed.connect(widget.load_data)`

### Adding Import Sources
1. Extend `BaseImporter`
2. Implement `import_all()` method
3. Use `session_scope()` for transactions

---

## 13. Performance Considerations

**Caching**:
- `GlobalResultsCache` - Wide format, indexed by result_set_id
- `ElementResultsCache` - Wide format, indexed by element_id + result_set_id
- `ResultDataService` - Multi-level in-memory caching

**Bulk Operations**:
- `bulk_create()` for batch inserts
- `bulk_save_objects()` for updates
- Session commits at end of import phase

**Lazy Loading**:
- Browser doesn't query data until node clicked
- Datasets cached until invalidated
- Plots only render visible data

---

## 14. Known Limitations

- Single-user desktop app (no concurrent access)
- SQLite limits (no server-side processing)
- Element results limited to piers (future: full 3D model)
- No time-history visualization yet

---

**For detailed code examples, see inline comments and docstrings.**
**For design patterns, see DESIGN.md**
**For quick tasks, see CLAUDE.md**


---

## 15. Version History Summary

### v2.7 (November 13, 2024) - Multi-Set Export & UI Enhancements
**Export System**:
- Multi-result-set export (select multiple DES/MCE/SLE simultaneously)
- Joint results export (SoilPressures, VerticalDisplacements)
- Single timestamp per export operation
- Export dialog redesigned (Result Types 40% | Result Sets + Options 60%)
- Type expansion: Global (directions), Element (V2/V3), Joint (_Min suffix handling)

**UI/UX**:
- Blur overlay for modal dialogs (200ms fade animations)
- Wide dialog layout pattern (1200x650+)
- Consistent checkbox styling with custom checkmarks
- Result type filtering (only show available types)
- Comparison dialog wide layout with 3-column display

**Comparison**:
- Joint comparison scatter plots (ComparisonJointScatterWidget)
- All joints view with load case X-axis
- Multi-result-set overlay with color coding

### v2.6 (November 12, 2024) - Foundation Results Summary
- Average/Maximum/Minimum columns for soil pressure tables
- Average/Maximum/Minimum columns for vertical displacement tables
- Summary columns in lighter gray for distinction
- Columns: Shell Object | Unique Name | [Load Cases] | Average | Maximum | Minimum

### v2.5 (November 12, 2024) - Foundation Results & Comparisons
- Soil Pressures: Full support (table, plot, comparison)
- Vertical Displacements: Full support (table, plot, comparison)
- Joint comparison type (load case-based organization)
- Reversed color scheme for foundation (orange_blue)
- Load case lexicographic sorting for foundation results
- Multi-file import with shared foundation joint list
- Prescan detection for soil pressures

### v2.4 (November 11, 2024) - Element Comparisons
- Element-level comparison support (walls, columns, beams)
- Individual element selection in tree (P1, C5, etc.)
- V2/V3 direction support for shears
- Element comparison titles with full context

### v2.3 (November 11, 2024) - Comparison View Design
- Custom comparison plot without tabs
- Rounded card legend on right side
- Ratio columns (last/first) instead of delta
- Centered table values with % for drifts only
- Dynamic table width, plot takes remaining space

### v2.2 (November 10, 2024) - Export Refinements
- Fixed export dialog height
- Reduced spacing (8px)
- Removed reload button
- Max/Min load cases lexicographically sorted

### v2.1 (November 8, 2024) - Comprehensive Export
- Auto-discovery export dialog
- Multi-format: Combined Excel, Per-file Excel/CSV
- Base type display with auto-expansion

### v2.0 (November 8, 2024) - Architecture Refactor
- BaseRepository pattern
- BaseImporter hierarchy
- Reusable UI components extracted

---

**End of Architecture Documentation**
**Last Updated**: November 13, 2024 | **Version**: 2.7
