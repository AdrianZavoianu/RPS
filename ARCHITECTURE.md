# RPS Architecture (Condensed)

**Version**: 2.14 | **Date**: 2024-12-02

> **Full details in code comments and docstrings. This doc covers key patterns only.**

---

## 1. System Overview

**RPS** = Results Processing System for structural engineering (ETABS/SAP2000)

**Stack**: PyQt6 (UI) + PyQtGraph (plots) + SQLite (data) + SQLAlchemy (ORM) + Pandas (processing)

**Architecture**: Layered (UI → Service → Repository → Database)

**New in v2.14**:
- **Context-Aware Export System**: Export dialog automatically filters result sets and types based on NLTHA/Pushover tab context. NLTHA tab shows only NLTHA result sets (no Curves option), Pushover tab shows only Pushover result sets with Curves + results. Independent selection allows exporting curves only, results only, or both.
- **Pushover Curve Export**: Integrated curves export into `ComprehensiveExportDialog`. Combined mode exports all curves to single Excel with separate sheets per case. Per-file mode creates one Excel per result set with sheets for each pushover case. CSV not supported for curves.
- **Result Set Filtering**: `_discover_result_sets()` filters by `analysis_type` attribute. Uses `.in_()` queries to discover result types across ALL result sets of the analysis type (not just current result set).
- **Smart Context Switching**: `export_nltha_results()` passes `analysis_context='NLTHA'`, `export_pushover_results()` passes `analysis_context='Pushover'`. Dialog title and labels dynamically update based on context.
- **Error Handling**: Shows warning dialog and rejects immediately if no result sets exist for selected context. Override `exec()` method to prevent showing empty dialog.

**New in v2.13**:
- **Pushover Joints Support**: Complete foundation results for pushover analysis (soil pressures, vertical displacements, joint displacements). Integrated directly into `PushoverGlobalImportDialog` worker thread - imports automatically with global results using same load case selection.
- **New Parsers**: `PushoverSoilPressureParser` extracts minimum soil pressures from "Soil Pressures" sheet. `PushoverVertDisplacementParser` reads foundation joint list from "Fou" sheet and filters "Joint Displacements" to extract minimum Uz values for foundation joints only.
- **Result Type Naming**: CRITICAL - Uses `_Min` suffix for cache storage (`SoilPressures_Min`, `VerticalDisplacements_Min`) to match NLTHA pattern and enable view reuse. Mismatch causes data display failures.
- **Tree Browser Integration**: New "Joints" section added to pushover result sets at same level as Curves/Global/Elements. Includes Plot + Table views for soil pressures and vertical displacements, plus Ux/Uy/Uz table views for joint displacements.
- **View Reuse**: Reuses existing NLTHA joint views (`load_all_soil_pressures`, `load_soil_pressures_table`, etc.) without duplication. Load case shorthand mapping automatically applied to all joint tables.

**New in v2.12**:
- **Pushover Load Case Mapping**: Shorthand names (Px1, Py1) automatically generated for long pushover load case names to improve UI readability. Mapping supports both hyphen (`Push-Mod-X+Ecc+`) and underscore (`Push_Mod_X+Ecc+`) formats used across global and element results. Preserved +/- eccentricity signs using negative lookbehind/lookahead regex patterns.
- **Automatic Context Detection**: Result set analysis type (`Pushover` vs `NLTHA`) automatically detected when navigating tree browser, eliminating manual tab switching. Context switching triggers appropriate mapping application.
- **Tree Browser Event Handlers**: Added missing click handlers for `pushover_column_result` (R2/R3 rotations) and `pushover_beam_result` (R3 plastic rotations) to enable element result navigation in pushover projects.

**New in v2.11**:
- Pushover global results import: Story drifts, forces, and displacements imported from folder and associated with existing curve result sets.
- Result set validation: `PushoverGlobalImportDialog` enforces workflow (curves first, then global results) with combo box selection.
- Parser direction filtering: Regex pattern `[_/]{direction}[+-]` correctly identifies pushover direction from output case names (not Excel Direction column).
- Story order preservation: Uses `.unique()` and Pandas Categorical to maintain Excel sheet order, matching NLTHA pattern.
- Cache build fix: `session.flush()` before cache building ensures all records are queryable.

**New in v2.10**:
- Pushover curve visualization: `PushoverCurveView` widget displays capacity curves (displacement vs base shear) with auto-sized table and plot.
- `PushoverParser` extracts curves from Excel files (Joint Displacements + Story Forces sheets), normalizes displacements, and returns `PushoverCurveData` objects.
- Table border fix: QTableWidget frame shape set to NoFrame project-wide to eliminate double borders (native frame + CSS border layering).
- Direction detection: Automatically identifies X/Y direction from pushover case names.

**New in v2.9**: Database connection management overhaul with engine registry and NullPool for Windows compatibility. Import dialog enhancements with proper button state management. Single-instance project windows with tracking. Modern web-style navigation header with larger fonts and cleaner design.

---

## 2. Data Model (26 Tables)

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

**Pushover Results** (2 tables, NEW in v2.10-2.11):
- `pushover_cases` - Capacity curves (step data) for each pushover case
- `pushover_curve_points` - Individual curve data points (displacement, base shear)

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

### Pushover Results Models (v2.10-2.11)

**PushoverCase**:
- Stores metadata for each pushover capacity curve
- Fields: `result_set_id`, `name`, `direction`, `base_story`
- One record per pushover case (e.g., "Push_Mod_X+Ecc+")
- Linked to `pushover_curve_points` via foreign key

**PushoverCurvePoint**:
- Stores individual data points on capacity curve
- Fields: `pushover_case_id`, `step_number`, `displacement`, `base_shear`
- Multiple points per pushover case (one per analysis step)
- Displacement normalized to zero initial value, absolute values

**Pushover Global Results** (reuses existing tables):
- `story_drifts` - Story drifts from pushover analysis (direction='X' or 'Y')
- `story_forces` - Story shears from pushover analysis
- `story_displacements` - Floor displacements from pushover analysis
- Same schema as NLTHA results, distinguished by `result_set.analysis_type='Pushover'`
- Uses `story_sort_order` to preserve Excel sheet order

**Import Workflow** (enforced by dialog):
1. **Curves First**: Import pushover curves → Creates result set with name (e.g., "160Will_Push")
2. **Global Results Second**: Import global results → Select existing result set from combo box
3. **Validation**: Dialog checks for existing pushover result sets, shows warning if none exist

**Direction Handling** (critical distinction):
- **Excel Direction Column** = Component direction (X or Y drift component)
- **Output Case Name** = Pushover direction (e.g., Push_Mod_**X**+Ecc+)
- Parser uses regex `[_/]{direction}[+-]` to filter by pushover direction
- All pushover cases report BOTH X and Y components (primary + cross drifts)

**Story Order Preservation** (matches NLTHA pattern):
- Uses `df['Story'].unique().tolist()` to preserve Excel first-occurrence order
- `groupby(..., sort=False)` prevents alphabetical sorting
- Restores order after groupby using Pandas Categorical
- Stores `story_sort_order` = 0-based Excel row index

**Cache Format**:
- Load case keys with direction suffix: `Push-Mod-X+Ecc+_X` (for X drifts)
- Underscores replaced with hyphens to prevent transformer splitting
- Direction suffixes: `_X/_Y` (drifts), `_VX/_VY` (forces), `_UX/_UY` (displacements)
- **Critical**: `session.flush()` called before cache building to ensure records are queryable

### Pushover Joints Results (v2.13)

**Integration**: Joints imported automatically with global results in `PushoverGlobalImportDialog` worker thread. No separate import dialog required.

**Soil Pressures**:
- **Parser**: `PushoverSoilPressureParser` reads "Soil Pressures" sheet
- **Data**: Minimum soil pressure per foundation element (Shell Object, Unique Name)
- **Direction Filtering**: Regex `{direction}[+-]?` matches pushover direction in output case names
- **Grouping**: Groups by (Shell Object, Unique Name, Output Case) and takes `.min()`
- **Storage**: `JointResultsCache` with `result_type='SoilPressures_Min'` (CRITICAL: `_Min` suffix required)
- **Order**: Preserves Excel element order using `.unique()` and Pandas Categorical
- **Example**: 720 elements × 2 load cases (Push Modal X, Push Uniform X) from 711Vic file

**Vertical Displacements**:
- **Parser**: `PushoverVertDisplacementParser` reads "Fou" + "Joint Displacements" sheets
- **Foundation Joints**: Reads joint list from "Fou" sheet first (e.g., joints 181-1133)
- **Filtering**: Filters "Joint Displacements" to only joints in Fou sheet
- **Data**: Minimum Uz (vertical displacement) per foundation joint from Min step type
- **Grouping**: Groups by (Story, Label, Unique Name, Output Case) and takes `.min()` on Uz
- **Storage**: `JointResultsCache` with `result_type='VerticalDisplacements_Min'` (CRITICAL: `_Min` suffix required)
- **Structure**: Story-Label-Unique Name preserved for each foundation joint
- **Example**: 953 joints × 2 load cases from 711Vic file

**Joint Displacements** (Ux, Uy, Uz):
- **Parser**: `PushoverJointParser` (already existed, now integrated into global import)
- **Data**: Absolute maximum displacement across Max/Min step types per joint/case
- **Components**: Three separate result types in cache
  - `JointDisplacements_Ux` - X-direction displacements
  - `JointDisplacements_Uy` - Y-direction displacements
  - `JointDisplacements_Uz` - Z-direction displacements
- **Storage**: `JointResultsCache` with separate entry per displacement type
- **All Joints**: Includes all joints (not filtered by Fou sheet like vertical displacements)

**Tree Structure**:
```
└── Pushover Result Set
    ├── Curves (X/Y directions)
    ├── Global Results (Drifts, Forces, Displacements)
    ├── Elements (Walls, Columns, Beams)
    └── ◆ Joints (NEW in v2.13)
        ├── Joint Displacements (Ux, Uy, Uz tables)
        ├── Soil Pressures (Plot + Table)
        └── Vertical Displacements (Plot + Table)
```

**View Reuse**: Uses existing NLTHA joint views without duplication
- `load_all_soil_pressures()` - Scatter plot widget (reused)
- `load_soil_pressures_table()` - Wide-format table (reused, uses beam_rotations_table widget)
- `load_all_vertical_displacements()` - Scatter plot widget (reused)
- `load_vertical_displacements_table()` - Wide-format table (reused)
- Load case shorthand mapping automatically applied to all joint tables

**Import Progress**:
- Joint displacements: 85-90% (alongside global results)
- Soil pressures: 90-95% (after global results)
- Vertical displacements: 95-100% (final step)

**CRITICAL Naming Convention**:
- Importers MUST store with `_Min` suffix: `SoilPressures_Min`, `VerticalDisplacements_Min`
- Tree browser checks for `_Min` suffix when determining section visibility
- Views query for `_Min` suffix when loading data
- Mismatch between importer and view will cause data display failures (empty views)

### Key Fields
- **Story ordering**: `sort_order` (global), `story_sort_order` (per-result)
- **Element type**: `element_type` in ('Wall', 'Quad', 'Column', 'Beam')
- **Cache columns**: JSON-serialized load case columns for dynamic querying

---

## 3. Database Connection Management (v2.9)

### Engine Registry Pattern

**Problem**: SQLAlchemy's default connection pooling caused file locking issues on Windows, preventing project deletion.

**Solution**: Centralized engine management with NullPool (`database/base.py`):

```python
# Global engine registry
_project_engines: Dict[str, Engine] = {}

def _get_or_create_engine(db_path: Path) -> Engine:
    """Reuse engines, avoid duplicates."""
    db_path_str = str(db_path.resolve())
    if db_path_str in _project_engines:
        return _project_engines[db_path_str]

    engine = create_engine(
        f"sqlite:///{db_path}",
        poolclass=NullPool,  # No pooling - closes connections immediately
        ...
    )
    _project_engines[db_path_str] = engine
    return engine

def dispose_project_engine(db_path: Path) -> None:
    """Explicitly close all connections."""
    db_path_str = str(db_path.resolve())
    if db_path_str in _project_engines:
        engine = _project_engines.pop(db_path_str)
        engine.dispose()
```

**Key Features**:
- **NullPool**: Connections close immediately after use (critical for SQLite on Windows)
- **Engine reuse**: Prevents duplicate engines for same database
- **Explicit disposal**: `dispose_project_engine()` ensures clean shutdown
- **Called on window close**: `ProjectDetailWindow.closeEvent()` disposes engine
- **Called before deletion**: `delete_project_context()` disposes before file removal

**Benefits**:
- No "file in use" errors on project deletion
- Immediate, clean database file deletion
- Proper connection lifecycle management
- No connection leaks

---

## 4. Configuration System

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

## 5. Key Patterns

### Observability & Diagnostics (v2.10)

- `utils/logging_utils.py` configures root logging with JSON lines written to `data/logs/rps.log` and simultaneously streams concise console output.
- Logging is initialized in `src/main.py` before Qt startup, so background threads (importers, prescans) inherit the configuration.
- `DataImporter`, folder import workers, and prescan services emit structured events (`import.start`, `import.phase`, `import.complete`, etc.), making it easy to trace long-running jobs.
- `gui/diagnostics_dialog.py` reads the latest log tail, shows metadata (size, refresh time), and exposes quick buttons to copy the log path or open the folder—accessible via the status bar “Diagnostics” button.

### Runtime & Controllers (v2.10)

- `services/project_runtime.py` encapsulates per-project SQLAlchemy session + repositories + `ResultDataService`. `ProjectDetailWindow` receives a runtime instance instead of creating repositories ad-hoc, ensuring consistent teardown via `dispose()`.
- `gui/controllers/project_controller.py` centralizes catalog operations (`ensure_context`, `list_summaries`, `delete_project`, `build_runtime`) so `MainWindow` handles UI only.
- Open project windows now hold onto runtimes; when a detail window closes, it releases the session cleanly, avoiding dangling connections.

### Import Task Registry & Aggregation (v2.10)

- `processing/import_tasks.py` defines declarative `ImportTask` objects (label, handler name, required sheets, stats phase). `DataImporter` iterates the tuple to decide what to load; adding a new result type is a one-line addition.
- `processing/import_stats.py` introduces `ImportStatsAggregator` used by the base and enhanced folder importers to sum numeric counts and collect warnings/errors consistently.
- Selective folder imports still layer on load-case filters but reuse the same aggregator so reports stay uniform.

### Fresh Tests

- `tests/test_import_tasks.py` exercises the task dispatcher and stats aggregator logic.
- `tests/test_project_runtime.py` validates the runtime builder for both success and failure cases, ensuring the GUI wiring can be tested headlessly.

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

## 6. Import Flow

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

## 7. Export Flow

### Export Results (v2.14 - Context-Aware Export)
1. User clicks "Export Results" button (behavior depends on active tab)
   - **NLTHA tab** → `export_nltha_results()` → `ComprehensiveExportDialog(analysis_context='NLTHA')`
   - **Pushover tab** → `export_pushover_results()` → `ComprehensiveExportDialog(analysis_context='Pushover')`

2. **Context-Aware Discovery**:
   - **Result Sets** (`_discover_result_sets()`):
     - NLTHA: Filter where `analysis_type != 'Pushover'`
     - Pushover: Filter where `analysis_type == 'Pushover'`
   - **Result Types** (`_discover_result_types()`):
     - Query across ALL result sets matching context (not just current)
     - NLTHA: Show Drifts, Forces, Elements, Joints (no Curves)
     - Pushover: Show **Curves** + Drifts, Forces, Elements, Joints
   - Show base types only (e.g., "Drifts", "SoilPressures", "Curves")

3. **Dialog Layout** (wide, 2-column):
   - **Header**: "Export NLTHA Results" or "Export Pushover Results"
   - **Info**: "Found X [context] result set(s) with Y result type(s)"
   - Left (40%): Result Types tree (Global | Element | Joint)
     - Pushover: "Curves" checkbox appears first under Global
   - Right (60%): Result Sets selector (filtered by context) + Export Options + Output

4. **User Selection**:
   - Result sets to export (only shows matching context)
   - Result types to export (expand to directions on export)
   - **Pushover flexibility**: Can select Curves only, Results only, or Both
   - Format (Excel/CSV) + combined/separate mode
   - Note: CSV not supported for Curves (requires multi-sheet format)

5. **Export Process** → `ComprehensiveExportWorker`
   - Generate **single timestamp** for entire operation
   - Iterate: `for result_set_id in selected_result_set_ids`
   - For each result type:
     - **Curves** (Pushover only):
       - Query `PushoverCase` and `PushoverCurvePoint` tables
       - Export each case as separate sheet: Step | Base Shear | Displacement
       - Combined mode: All curves in single Excel with sheets like `{ResultSet}_{CaseName}`
       - Per-file mode: One Excel per result set with sheet per case
     - **Global**: Query with `get_standard_dataset(result_type, direction, result_set_id)`
     - **Element**: Query with `get_element_export_dataframe(result_type, result_set_id)`
     - **Joint**: Query with `get_joint_dataset(result_type + '_Min', result_set_id)`
   - Write files/sheets: `{result_set_name}_{result_type}_{timestamp}.xlsx`

6. **Type Expansion** (`_get_selected_result_types()`):
   - **Curves**: No expansion (used as-is)
   - **Global**: Find all directional variants in RESULT_CONFIGS (Drifts → Drifts_X, Drifts_Y)
   - **Element**: Query cache across ALL matching result sets for `{base_type}_V2`, `{base_type}_V3`, `{base_type}_R2`, `{base_type}_R3` variants
   - **Joint**: Query cache for `{base_type}_Min`, `{base_type}_Ux`, `{base_type}_Uy`, `{base_type}_Uz` variants

**Key Features**:
- **Fully independent**: NLTHA and Pushover exports never mix result sets
- **Context filtering**: Automatic filtering by `analysis_type` attribute
- **Flexible selection**: Export curves only, results only, or both (Pushover)
- **Multi-result-set**: Export multiple result sets in one operation
- **Single timestamp**: All files share timestamp for grouping
- **Error handling**: Warning dialog if no result sets exist for context
- **Smart discovery**: Queries across all matching result sets for comprehensive type list

### Export Project
1. User clicks "Export Project" → `ExportProjectExcelDialog`
2. Export all data → `ProjectExportService`
3. Create human-readable sheets + IMPORT_DATA (JSON)
4. Write .xlsx → Can be re-imported via `ImportProjectDialog`

---

## 8. UI Architecture

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

### Pushover Curve Feature (v2.10)

**Purpose**: Visualize nonlinear static pushover analysis capacity curves (displacement vs base shear)

**Components**:
- `PushoverCurveView` (`gui/result_views/pushover_curve_view.py`) - Main visualization widget
- `PushoverParser` (`processing/pushover_parser.py`) - Excel file parser
- `PushoverCurveData` - Data container class

**Parser** (`PushoverParser`):
```python
class PushoverParser:
    def parse_curves(self, base_story: str) -> Dict[str, PushoverCurveData]:
        # 1. Extract displacements from "Joint Displacements" sheet
        displacement_data = self._parse_displacements()

        # 2. Extract base shears from "Story Forces" sheet
        shear_data = self._parse_base_shears(base_story)

        # 3. Merge by matching step numbers
        curves = self._merge_data(displacement_data, shear_data)

        return curves
```

**Key Features**:
- **Displacement Parsing**: Extracts Ux/Uy columns from "Joint Displacements"
  - Determines direction from case name (X or Y)
  - Normalizes: Subtracts initial value, then takes absolute value
  - Groups by "Output Case" name

- **Base Shear Parsing**: Extracts VX/VY columns from "Story Forces"
  - Filters by base story (typically foundation or first floor)
  - Filters by location = "Bottom"
  - Takes absolute values of shear forces
  - Groups by "Output Case" name

- **Data Merging**: Matches displacement and shear by step number
  - Only includes points where step numbers align
  - Returns `PushoverCurveData` objects with arrays: step_numbers, displacements, base_shears

**View** (`PushoverCurveView`):

**Layout**:
- Horizontal `QSplitter` with two panels
- Left panel: Table (auto-sized to content)
- Right panel: Plot (takes remaining space)
- Stretch factors: Table=1, Plot=2

**Table Features**:
- 3 columns: Step (50px) | Base Shear (kN) (120px) | Displacement (mm) (140px)
- Auto-sizing: Calculates exact height after data loads
  ```python
  total_height = header_height + sum(row_heights) + 2  # 2px border
  self.table.setFixedHeight(total_height)
  ```
- Size policy: Fixed vertical, Preferred horizontal
- Alignment: AlignTop within container
- No vertical scrolling (table sized to fit all rows)
- Frame shape: NoFrame (eliminates double border with CSS)
- Border: CSS only (`border: 1px solid #2c313a`)

**Plot Features**:
- X-axis: Displacement (mm)
- Y-axis: Base Shear (kN)
- Range: Starts at (0,0) with 5% padding
  ```python
  self.plot_widget.setXRange(0, max_disp * 1.05, padding=0)
  self.plot_widget.setYRange(0, max_shear * 1.05, padding=0)
  ```
- Line: Teal (#4a7d89), 2px width
- Symbols: Circles, 8px, teal fill
- Grid: Enabled with 50% alpha
- Mouse: Disabled (no pan/zoom)
- Auto-range: Disabled
- SI prefix: Disabled (raw units only)

**Border Fix**:
- Problem: QTableWidget has native frame (QAbstractScrollArea) + CSS border = double border
- Solution: `self.table.setFrameShape(QFrame.Shape.NoFrame)`
- Result: Only CSS border renders, clean single border
- Applied to: `PushoverCurveView` table + `ResultsTableWidget` (project-wide fix)

**Styling Consistency**:
- Matches NLTHA results tables (dark theme, teal accent)
- Same fonts: Inter 10pt for table content
- Same colors: Background #0a0c10, Card #161b22, Accent #4a7d89
- Same borders: 1px solid #2c313a
- No rounded corners (border-radius removed project-wide)

**Usage Flow**:
1. User opens pushover Excel file (contains "Joint Displacements" and "Story Forces" sheets)
2. Instantiate `PushoverParser(file_path)`
3. Call `parser.parse_curves(base_story='Story1')` to extract curves
4. Create `PushoverCurveView()` widget
5. Call `view.display_curve(case_name, step_numbers, displacements, base_shears)`
6. View auto-sizes table and plots curve

### Pushover Load Case Mapping (v2.12)

**Purpose**: Simplify display of long pushover load case names (e.g., `Push-Mod-X+Ecc+` → `Px1`) in table headers and legends

**Components**:
- `pushover_utils.py` - Mapping generation utility
- `project_detail_window.py` - Mapping cache and application logic
- `results_table_widget.py` - Table header mapping
- `results_plot_widget.py` - Legend mapping

**Mapping Generation** (`create_pushover_shorthand_mapping`):
```python
def create_pushover_shorthand_mapping(load_case_names: list, direction: str = None) -> Dict[str, str]:
    # Auto-detect X and Y directions from case names
    x_cases = [name for name in load_case_names if '_X' in name or '-X' in name]
    y_cases = [name for name in load_case_names if '_Y' in name or '-Y' in name]

    # Map X direction: Px1, Px2, ...
    for idx, name in enumerate(sorted(x_cases), start=1):
        mapping[name] = f"Px{idx}"

    # Map Y direction: Py1, Py2, ...
    for idx, name in enumerate(sorted(y_cases), start=1):
        mapping[name] = f"Py{idx}"

    return mapping
```

**Dual-Format Support**:
- **Problem**: Global results use hyphens (`Push-Mod-X+Ecc+`), element results use underscores (`Push_Mod_X+Ecc+`)
- **Solution**: Extended mapping with both variants using regex pattern
  ```python
  # Regex: Replace - that is NOT preceded/followed by 'Ecc' (preserves +/- signs)
  underscore_variant = re.sub(r'(?<!Ecc)-(?!Ecc)', '_', full_name)
  # Push-Mod-X+Ecc- → Push_Mod_X+Ecc- (NOT Push_Mod_X+Ecc_)
  ```
- **Result**: 32 mapping entries (16 base + 16 underscore variants)

**Mapping Cache** (`project_detail_window.py`):
- Created once per result set during project load
- Stored in `self._pushover_mappings` dict (result_set_id → mapping)
- Retrieved via `_get_pushover_mapping(result_set_id)` returning a copy to prevent cache corruption

**Application Flow**:
1. On project load: Query distinct load cases from cache for each pushover result set
2. Strip direction suffixes (`_UX`, `_UY`, `_VX`, `_VY`) before creating mapping
3. Generate base mapping using `create_pushover_shorthand_mapping()`
4. Extend mapping with underscore variants
5. Cache mapping in memory
6. When loading results:
   - Check if `active_context == "Pushover"`
   - Retrieve mapping for current result set
   - Pass mapping to table and plot widgets
   - Widgets apply mapping to headers/legends

**Automatic Context Switching**:
- Triggered in `on_browser_selection_changed()` when tree item clicked
- Checks `result_set.analysis_type` attribute
- Switches to "Pushover" context if `analysis_type == "Pushover"`
- Switches to "NLTHA" context otherwise
- Eliminates manual tab clicking

**Widget Implementation**:
- **Table Widget**: Replaces column header names with shorthand
  ```python
  if shorthand_mapping is not None:
      display_names = [shorthand_mapping.get(name, name) for name in column_names]
      self.table.setHorizontalHeaderLabels(display_names)
  ```
- **Plot Widget**: Shows full mapping in legend
  ```python
  if label in self._shorthand_mapping:
      shorthand = self._shorthand_mapping[label]
      display_label = f"{shorthand} = {label}"  # "Px1 = Push-Mod-X+Ecc+"
  ```

**Applied To**:
- Standard view (global, element, joint results)
- Wide-format tables (beam rotations, soil pressures, vertical displacements)
- Comparison views (preserved for future implementation)

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

## 9. Story Ordering System

**Problem**: Different Excel sheets have different story orders

**Solution**: Dual ordering system
- **Global**: `Story.sort_order` from "Story Drifts" sheet (0=bottom)
- **Per-Result**: `<result>.story_sort_order` from each sheet (0=first row)

**Display**:
- Plots: Bottom floors at y=0, top floors at y=max (ascending)
- Tables: Bottom floors first, top floors last (ascending)

**Exception**: Quad rotations always use global order (Excel sorted by element name, not height)

---

## 10. Design System (DESIGN.md)

**Colors**:
- Background: `#0a0c10`, Card: `#161b22`
- Accent: `#4a7d89` (teal), `#67e8f9` (cyan)
- Text: `#d1d5db`, Muted: `#9ca3af`

**Spacing**: 4px increments (4, 8, 12, 16, 24)

**Typography**: 14px base, 24px headers, 13px muted text

**Gradient Colors**: `blue_orange`, `green_red`, `purple_yellow`
- `get_gradient_color(value, min, max, scheme)` → QColor

---

## 11. Testing

**Unit Tests** (`tests/`):
- Stub pattern for database access
- Mock pattern for external dependencies
- Pytest fixtures for common setups

**Test Coverage**:
- Repository layer: CRUD operations
- Service layer: Dataset building
- Transformer layer: Excel → Model conversion

---

## 12. Migration & Deployment

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

## 13. Extension Points

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

## 14. Performance Considerations

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

## 15. Known Limitations

- Single-user desktop app (no concurrent access)
- SQLite limits (no server-side processing)
- Element results limited to piers (future: full 3D model)
- No time-history visualization yet

---

**For detailed code examples, see inline comments and docstrings.**
**For design patterns, see DESIGN.md**
**For quick tasks, see CLAUDE.md**


---

## 16. Version History Summary

### v2.12 (November 26, 2024) - Pushover Load Case Mapping & UX Improvements
**Load Case Shorthand Mapping**:
- Automatic mapping of long pushover load case names to shorthand (Px1, Py1, Px2, Py2, etc.)
- Mapping displayed in both table headers (shorthand only) and plot legends (full mapping: "Px1 = Push-Mod-X+Ecc+")
- Created once per result set during project load and cached in memory (`_pushover_mappings` dict)
- Retrieved via `_get_pushover_mapping()` returning a copy to prevent cache corruption
- Applied to standard view (global/element/joint results) and wide-format tables (beam rotations, soil pressures, vertical displacements)
- Location: `utils/pushover_utils.py`, `project_detail_window.py:582-640`

**Dual-Format Support**:
- Extended mapping handles both hyphen (`Push-Mod-X+Ecc+`) and underscore (`Push_Mod_X+Ecc+`) naming conventions
- Global results use hyphens, element results use underscores
- Regex pattern `(?<!Ecc)-(?!Ecc)` preserves +/- eccentricity signs when converting hyphens to underscores
- Results in 32 mapping entries (16 base cases + 16 underscore variants)
- Mapping covers all load cases including positive/negative directions and eccentricities

**Automatic Context Switching**:
- App automatically detects `ResultSet.analysis_type` attribute when navigating tree browser
- Switches to "Pushover" context for pushover result sets, "NLTHA" context otherwise
- Eliminates manual tab clicking requirement
- Context switching triggers appropriate mapping application
- Implementation in `on_browser_selection_changed()` (line 658-677)

**Tree Browser Event Handlers**:
- Added missing click handlers for `pushover_column_result` type (R2/R3 column rotations)
- Added missing click handlers for `pushover_beam_result` type (R3 plastic beam rotations)
- Handlers extract base result type from suffixed types (`ColumnRotations_R2` → `ColumnRotations`)
- Enables navigation to column and beam element results in pushover projects
- Location: `results_tree_browser.py:1557-1575`

**Error Handling**:
- Graceful fallback to original headers if mapping fails
- Try/catch blocks in wide-format table mapping application
- Debug logging for troubleshooting mapping issues

### v2.11 (November 23, 2024) - Pushover Global Results
**Pushover Global Results Import**:
- `PushoverGlobalImportDialog` enforces workflow: curves first, then global results
- Result set selection via combo box (not text input)
- Validates existing pushover result sets on init
- Shows warning dialog if no curves imported yet
- Imports Story Drifts, Story Forces, Floor Displacements from folder
- X and Y direction load case selection (separate columns)

**Parser Direction Filtering**:
- Fixed Excel Direction column interpretation (component vs pushover direction)
- Direction column = drift/force COMPONENT (X or Y), not pushover direction
- Pushover direction from Output Case NAME using regex: `[_/]{direction}[+-]`
- All pushover cases report both X and Y components (primary + cross)

**Story Order Preservation**:
- Uses `df['Story'].unique().tolist()` to preserve Excel first-occurrence order
- `groupby(..., sort=False)` prevents alphabetical sorting
- Restores order after groupby using Pandas Categorical
- Stores `story_sort_order` = 0-based Excel row index
- Matches NLTHA pattern for consistent display

**Cache Build Fix**:
- Added `session.flush()` before `_build_cache()` (line 137)
- Critical fix: Ensures all imported records are queryable
- Cache was incomplete because records weren't flushed before query
- Now all stories and directions appear correctly

**Tree Browser Structure**:
- Global Results at same level as Curves (not nested)
- Three result types: Story Drifts, Story Forces, Floor Displacements
- X and Y subsections under each result type

**Load Case Handling**:
- Replaces underscores with hyphens in cache keys
- `Push_Mod_X+Ecc+` → `Push-Mod-X+Ecc+_X` (for X drifts)
- Direction suffix prevents transformer confusion

### v2.10 (November 22, 2024) - Pushover Curve Visualization
**Pushover Curve Visualization**:
- New `PushoverCurveView` widget for capacity curve visualization
- Horizontal splitter layout: auto-sized table (left) + stretch plot (right)
- 3-column table: Step | Base Shear (kN) | Displacement (mm)
- Auto-sizing via exact height calculation after data load
- Plot: Displacement X-axis, Base Shear Y-axis, range from (0,0) with 5% padding
- Line style: Teal (#4a7d89) 2px with circle symbols (8px)
- No mouse interaction (pan/zoom disabled), fixed range display

**Pushover Parser**:
- `PushoverParser` class extracts capacity curves from Excel files
- Parses "Joint Displacements" sheet for displacement data (Ux/Uy columns)
- Parses "Story Forces" sheet for base shear data (VX/VY columns)
- Filters by base story + bottom location for shear extraction
- Normalizes displacements: subtracts initial value, takes absolute
- Merges data by matching step numbers
- Returns `PushoverCurveData` objects (step_numbers, displacements, base_shears)
- Automatic X/Y direction detection from case names

**Table Border Fix** (project-wide):
- QTableWidget double border issue resolved
- Problem: Native QAbstractScrollArea frame + CSS border = double layering
- Solution: `setFrameShape(QFrame.Shape.NoFrame)` on all tables
- Applied to: `PushoverCurveView` and `ResultsTableWidget`
- Result: Clean single border from CSS only (`border: 1px solid #2c313a`)

**Styling Consistency**:
- Matches NLTHA results: dark theme, teal accent, Inter 10pt font
- Removed rounded corners project-wide (border-radius eliminated)
- Consistent spacing, colors, borders across all result views

### v2.9 (November 15, 2024) - Database Connection Management & UX Polish
**Database Connection Management**:
- Engine registry pattern with centralized tracking (`_project_engines` dict)
- NullPool implementation for SQLite (no connection pooling)
- `dispose_project_engine()` function for explicit cleanup
- Engine disposal on window close (`ProjectDetailWindow.closeEvent()`)
- Engine disposal before project deletion (`delete_project_context()`)
- Eliminates "file in use" errors on Windows during deletion

**Import Dialog**:
- Start Import button properly disabled during file scanning
- Button state tracked through scan lifecycle (scan_worker is None check)
- `update_import_button()` called on scan start, completion, and error
- Prevents premature import attempts

**Project Window Management**:
- Single-instance window tracking (`_project_windows` dict in MainWindow)
- Duplicate prevention: existing windows brought to front
- Automatic cleanup via `destroyed` signal
- Windows explicitly closed before project deletion
- No orphaned windows or duplicate instances

**Navigation UI**:
- Font size increased from 16px to 22px (37.5% larger)
- Vertical padding reduced from 12px to 8px (tighter header)
- Underline effect removed (cleaner web-style look)
- Bold weight indicates active navigation (font-weight 600)
- Transparent backgrounds on all states (no hover backgrounds)
- Zero border radius for crisp, flat appearance

### v2.8 (November 15, 2024) - Import System Refactor
**Service Layer**:
- `ImportPreparationService` extracted to `services/import_preparation.py`
- Parallel file scanning with `ThreadPoolExecutor` (6 workers)
- `PrescanResult` and `FilePrescanSummary` data models
- Pure functions: `detect_conflicts()`, `determine_allowed_load_cases()`

**Provider Pattern**:
- `StandardDatasetProvider` (global/story-based results with caching)
- `ElementDatasetProvider` (element-specific results with caching)
- `JointDatasetProvider` (foundation/joint results with caching)
- Independent cache management per provider

**Repository Separation**:
- `ElementResultQueryRepository` in `element_result_repository.py`
- Model registry pattern for element types (Walls, Columns, Beams, Quads)
- Separation: CRUD (BaseRepository) vs complex queries (specialized repos)

### v2.14 (December 2, 2024) - Context-Aware Export System
**Export System**:
- Context-aware filtering: Export dialog filters result sets and types by `analysis_type` attribute
- NLTHA context: Shows only NLTHA result sets, no Curves option
- Pushover context: Shows only Pushover result sets with Curves + results
- Independent selection: Export curves only, results only, or both (Pushover)
- Pushover curve export: Integrated into `ComprehensiveExportDialog`
  - Combined mode: All curves in single Excel with sheets per case
  - Per-file mode: One Excel per result set with sheets per case
  - CSV not supported for curves (requires multi-sheet format)
- Smart discovery: Query result types across ALL matching result sets (not just current)
- Error handling: Warning dialog if no result sets exist for context
- UI updates: Dialog title/labels dynamically reflect analysis context

**Architecture**:
- `_discover_result_sets()`: Filter by `analysis_type != 'Pushover'` (NLTHA) or `== 'Pushover'` (Pushover)
- `_discover_result_types()`: Use `.in_(result_set_ids)` to query across all matching sets
- `_get_selected_result_types()`: Expand base types using all matching result set IDs
- `exec()` override: Reject dialog immediately if no data for context
- Context parameter: Passed from `export_nltha_results()` and `export_pushover_results()`

**Worker Threads**:
- `ComprehensiveExportWorker._export_combined()`: Handle Curves alongside global/element/joint
- `ComprehensiveExportWorker._export_per_file()`: Per-file curve export with pandas ExcelWriter
- Progress tracking: Curves integrated into existing progress system

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
**Last Updated**: December 2, 2024 | **Version**: 2.14
