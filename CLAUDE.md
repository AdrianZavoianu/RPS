# CLAUDE.md - Quick Development Guide

**RPS (Results Processing System)** - Structural engineering results processor (ETABS/SAP2000)
**Stack**: PyQt6 + PyQtGraph + SQLite + SQLAlchemy + Pandas
**Status**: Production-ready (v2.19 - December 2024 - ResultsTreeBrowser Decomposition)

---

## Documentation Structure
- **CLAUDE.md** (this file): Quick development tasks
- **ARCHITECTURE.md**: Technical architecture, data model
- **PRD.md**: Product requirements
- **DESIGN.md**: Visual design system

---

## Development Commands

```bash
# Setup
pipenv install --dev
pipenv run alembic upgrade head

# Run
pipenv run python src/main.py
pipenv run python dev_watch.py  # Hot-reload

# Test
pipenv run pytest tests/ -v

# Build
pipenv run pyinstaller src/main.py --onefile --windowed --name RPS
```

---

## Key Architecture Patterns

### Configuration-Driven Result Types
**Add new result type in ~10 lines:**
```python
# config/result_config.py
RESULT_CONFIGS['NewType'] = ResultTypeConfig(
    name='NewType', unit='kN', direction='X',
    color_scheme='blue_orange', decimal_places=2
)

# processing/result_transformers.py
TRANSFORMERS['NewType'] = NewTypeTransformer()
```

### Repository Pattern
```python
# All repos extend BaseRepository[Model] - CRUD is automatic
class MyRepository(BaseRepository[MyModel]):
    model = MyModel

    def custom_query(self):
        return self.session.query(self.model).filter(...).all()
```

### Data Model (24 tables)
- **Catalog**: CatalogProject (1 table)
- **Per-Project**: Project, Story, LoadCase, ResultSet, ComparisonSet, Element (6 tables)
- **Global Results**: StoryDrift, StoryAcceleration, StoryForce, StoryDisplacement (4 tables)
- **Element Results**: WallShear, QuadRotation, ColumnShear, ColumnAxial, ColumnRotation, BeamRotation (6 tables)
- **Foundation Results**: SoilPressure, VerticalDisplacement (2 tables)
- **Cache**: GlobalResultsCache, ElementResultsCache, JointResultsCache, AbsoluteMaxMinDrift (4 tables)
- **Future**: TimeHistoryData, ResultCategory (2 tables)

---

## Common Tasks

### Export System (v2.14 - Context-Aware)
- **Context-Aware Export**: Automatically filters result sets and types based on NLTHA/Pushover tab
  - **NLTHA Tab**: Shows only NLTHA result sets and types (no Curves option)
  - **Pushover Tab**: Shows only Pushover result sets with Curves + global/element/joint results
  - **Independent Selection**: Export curves only, results only, or both
- **Multi-Format**: Combined Excel (single file with multiple sheets) or Per-File (separate files)
- **Multi-Result-Set**: Export from multiple result sets simultaneously with single timestamp
- **Auto-Discovery**: Queries cache tables across all result sets of the analysis type
- **Export Project**: Complete project export for re-import (.xlsx)
- Location: `gui/export_dialog.py`, `services/export_service.py`

**Usage (NLTHA):**
1. Navigate to NLTHA tab
2. Click "Export Results" button
3. Select result sets (DES, MCE, SLE) and result types (Drifts, Forces, Elements, Joints)
4. Choose format (Excel or CSV) and output location
5. Export creates files with all selected data

**Usage (Pushover):**
1. Navigate to Pushover tab
2. Click "Export Results" button
3. Select pushover result sets and choose what to export:
   - ☑ Curves only → Exports capacity curves
   - ☑ Results only → Exports drifts, forces, elements, joints
   - ☑ Both → Exports curves + all results
4. Export creates files with all selected data

### Import System
- **Folder Import**: Batch import with load case selection, conflict resolution
- **File Import**: Single file validation and import
- **Foundation Support**: Vertical displacements use shared foundation joint list from Fou sheet across all files
- **Soil Pressure Detection**: Automatically detects soil pressure sheets during prescan
- Location: `gui/folder_import_dialog.py`, `processing/enhanced_folder_importer.py`

### Pushover Analysis System (v2.10)

**Import Workflow (IMPORTANT - Must follow this order):**
1. **First**: Import Pushover Curves → Create and name result set (e.g., "160Will_Push")
2. **Second**: Import Global Results → Select existing result set to add data to

#### Pushover Curves
- **Data Source**: Single Excel file with "Joint Displacements" and "Story Forces" sheets
- **Visualization**: Table (Step | Base Shear | Displacement) + Plot (displacement X-axis, base shear Y-axis)
- **Base Story Selection**: Specify base story for shear force extraction (typically foundation or first floor)
- **Direction Support**: Automatically detects X/Y direction from case names (_X+, _Y+, etc.)
- **Auto-Sizing**: Table auto-fits to content height, no scrolling or container borders
- Location: `gui/pushover_import_dialog.py`, `gui/result_views/pushover_curve_view.py`, `processing/pushover_parser.py`

**Parser Features** (`PushoverParser`):
- Parse displacement data from "Joint Displacements" sheet
- Parse base shear data from "Story Forces" sheet (filtered by base story + bottom location)
- Normalize displacements (zero initial value, absolute values)
- Merge displacement and shear data by matching step numbers
- Returns `PushoverCurveData` objects with step_numbers, displacements, base_shears

**View Features** (`PushoverCurveView`):
- Horizontal splitter layout: table left (auto-sized), plot right (remaining space)
- 3-column table: Step (narrow 50px) | Base Shear (120px) | Displacement (140px)
- Table auto-calculates exact height after data loads via `setFixedHeight()`
- Plot range from (0,0) with 5% padding, no mouse interaction
- Matches NLTHA styling: dark theme, teal accent (#4a7d89), no rounded corners
- Frame shape set to NoFrame to eliminate double borders (CSS border only)

#### Pushover Global Results
- **Data Source**: Folder of Excel files with "Story Drifts", "Story Forces", "Joint Displacements" sheets
- **Result Types**: Story Drifts, Story Forces (shears), Floor Displacements
- **Directions**: X and Y (separate load case selection for each direction)
- **Story Ordering**: Preserves Excel sheet order using `.unique()` and Pandas Categorical
- **Result Set Validation**: Must import curves first - dialog checks for existing pushover result sets
- **Cache Building**: Uses `session.flush()` before cache to ensure all records are written
- Location: `gui/pushover_global_import_dialog.py`, `processing/pushover_global_importer.py`, `processing/pushover_global_parser.py`

**Parser Features** (`PushoverGlobalParser`):
- Filters by pushover direction using regex pattern: `[_/]{direction}[+-]` (matches _X+, _Y-, etc.)
- Direction column in Excel = component (X/Y drift), NOT pushover direction
- Pushover direction comes from Output Case NAME (e.g., Push_Mod_**X**+Ecc+)
- All pushover cases report BOTH X and Y components (primary + cross drifts)
- Preserves story order from Excel using `.unique()` (first-occurrence order)
- Uses `groupby(..., sort=False)` to prevent alphabetical sorting
- Restores order after groupby using Pandas Categorical

**Importer Features** (`PushoverGlobalImporter`):
- Creates or gets existing result set (selected from combo box)
- Tracks story order from Excel (`self.story_order` dictionary)
- Stores `story_sort_order` per record (Excel row index)
- Builds cache with direction suffixes: _X/_Y for drifts, _VX/_VY for forces, _UX/_UY for displacements
- Replaces underscores with hyphens in load case names to prevent transformer splitting
- **CRITICAL**: Calls `session.flush()` before `_build_cache()` to ensure records are queryable

**Dialog Features** (`PushoverGlobalImportDialog`):
- Checks for existing pushover result sets on init (`_load_existing_result_sets()`)
- Shows warning and closes if no result sets exist
- Combo box populated with existing result set names (not text input)
- Load case selection by direction (X and Y columns)
- Select All / Select None buttons per direction

#### Pushover Joints (v2.13)
- **Data Source**: Same Excel files used for global results (with "Soil Pressures", "Fou", "Joint Displacements" sheets)
- **Result Types**: Soil Pressures, Vertical Displacements, Joint Displacements (Ux, Uy, Uz)
- **Import Integration**: Automatically imported alongside global results - no separate import step required
- **Directions**: X and Y (uses same load case selection as global results)
- **Foundation Joint Detection**: Uses Fou sheet to identify foundation joints for vertical displacements
- Location: `processing/pushover_soil_pressure_parser.py`, `processing/pushover_vert_displacement_parser.py`

**Soil Pressure Parser** (`PushoverSoilPressureParser`):
- Parses "Soil Pressures" sheet for minimum soil pressure per foundation element
- Filters by pushover direction using regex: `{direction}[+-]?` (matches X+, X-, Y+, Y-, X, Y)
- Groups by Shell Object, Unique Name, Output Case and takes minimum pressure
- Stores with result_type = "SoilPressures_Min" in JointResultsCache
- Preserves element order from Excel using `.unique()` and Pandas Categorical

**Vertical Displacement Parser** (`PushoverVertDisplacementParser`):
- Reads foundation joint list from "Fou" sheet (e.g., joints 181-1133)
- Parses "Joint Displacements" sheet filtered to foundation joints only
- Extracts minimum Uz (vertical) displacement per joint/case from Min step type
- Stores with result_type = "VerticalDisplacements_Min" in JointResultsCache
- Preserves Story-Label-Unique Name structure for each foundation joint

**Joint Displacement Importer** (`PushoverJointImporter`):
- Parses "Joint Displacements" sheet for Ux, Uy, Uz displacements
- Takes absolute maximum across Max/Min step types per joint/case
- Stores separately as "JointDisplacements_Ux", "JointDisplacements_Uy", "JointDisplacements_Uz"
- Wide-format table with all joints and load cases

**Tree Browser Structure**:
```
└── Pushover Result Set (e.g., "711Vic_Push")
    ├── Curves
    ├── Global Results
    ├── Elements
    └── ◆ Joints (NEW in v2.13)
        ├── › Joint Displacements
        │   ├── Ux (mm)
        │   ├── Uy (mm)
        │   └── Uz (mm)
        ├── › Soil Pressures (Min)
        │   ├── Plot (Scatter plot of all foundation elements)
        │   └── Table (Wide-format table)
        └── › Vertical Displacements (Min)
            ├── Plot (Scatter plot of all foundation joints)
            └── Table (Wide-format table)
```

**CRITICAL**: Result type naming uses `_Min` suffix:
- Soil pressures stored as `"SoilPressures_Min"` (not `"SoilPressures"`)
- Vertical displacements stored as `"VerticalDisplacements_Min"` (not `"VerticalDisplacements"`)
- Views query for `_Min` suffix - mismatch will cause display errors

### Comparison System
- **Create Comparison**: Compare multiple result sets (DES vs MCE vs SLE)
- **Multi-Series Plots**: All result sets overlaid on same building profile with color-coded legend
- **Averaged Data**: Shows per-story averages across all load cases
- **Ratio Columns**: Last/first result set ratio (e.g., MCE/DES = 1.68)
- **Persistent Storage**: Comparison sets saved in database (ComparisonSet table)
- **Browser Integration**: Comparison sets (COM1, COM2, etc.) appear alongside regular result sets
- **Global, Element & Joint Support**: Compare global results (Drifts, Forces), element-specific results (Wall P1, Column C5), and foundation results (Soil Pressures, Vertical Displacements)
- Location: `gui/comparison_set_dialog.py`, `gui/result_views/comparison_view.py`
- Data: `processing/result_service/comparison_builder.py`

**Global Results Usage:**
1. Click "Create Comparison" button in project header
2. Select ≥2 result sets to compare (e.g., DES, MCE, SLE)
3. Select result types to include (Drifts, Forces, etc.)
4. Enter name (COM1, COM2, etc.) and optional description
5. Comparison set appears in browser tree
6. Click result type (e.g., "Drifts X")
7. View shows table (Story | DES_Avg | MCE_Avg | MCE/DES) and multi-series plot

**Element Results Usage:**
1. Navigate to comparison set in tree (e.g., COM1)
2. Expand Elements → Walls/Columns/Beams
3. Expand result type (e.g., Shears)
4. Expand element (e.g., P1)
5. Click direction (e.g., V2 or V3 for shears, or single option for rotations)
6. View shows comparison for that specific element across all result sets

**Joint Results Usage (Foundation):**
1. Navigate to comparison set in tree (e.g., COM1)
2. Expand Joints → Soil Pressures or Vertical Displacements
3. Click specific foundation element (e.g., F1)
4. View shows load case comparison (Load Case | DES_Avg | MCE_Avg | MCE/DES)

**Comparison View Features:**
- **Table**: Centered values, no units except % for drifts, ratio column (2 decimals)
- **Plot**: Custom legend with rounded card items on right side
- **Layout**: Table takes content width, plot takes remaining space

### Adding UI Components
Follow DESIGN.md:
- Colors: `COLORS['card']` (#161b22), `COLORS['accent']` (#4a7d89)
- Spacing: 4px increments (4, 8, 12, 16, 24)
- Font: 14px base, 24px headers
- Use `create_styled_button()`, `create_styled_label()` from `ui_helpers.py`

### Story Ordering
- **Global order**: `Story.sort_order` from Story Drifts sheet
- **Per-result order**: `<result>.story_sort_order` preserves Excel row order
- **Exception**: Quad rotations always use global order (Excel sorted by element name)

---

## Key File Locations

**Configuration:**
- `config/result_config.py` - Result type definitions
- `config/visual_config.py` - Colors, styling

**Data Access:**
- `database/models.py` - All 24 ORM models (includes SoilPressure, VerticalDisplacement)
- `database/repositories/` - Domain-specific repositories (decomposed package)
  - `project.py` - ProjectRepository
  - `load_case.py` - LoadCaseRepository
  - `story.py` - StoryRepository, StoryDriftDataRepository, ResultRepository
  - `result_set.py` - ResultSetRepository, ComparisonSetRepository
  - `element.py` - ElementRepository
  - `cache.py` - CacheRepository, ElementCacheRepository, JointCacheRepository
  - `foundation.py` - SoilPressureRepository, VerticalDisplacementRepository
  - `pushover.py` - PushoverCaseRepository
- `database/repository.py` - Re-exports from repositories/ for backward compatibility
- `database/base_repository.py` - Generic CRUD operations
- `database/element_result_repository.py` - Element result queries (max/min aggregation)
- `processing/result_service/` - Data retrieval layer (7 focused modules)
  - `service.py` - Main facade with provider-based architecture
  - `providers.py` - Dataset providers (Standard, Element, Joint) with LRU caching
  - `cache_builder.py` - Dataset construction from cache
  - `comparison_builder.py` - Multi-set comparison logic
  - `maxmin_builder.py` - Max/min envelope calculations
  - `metadata.py` - Display label generation
  - `story_loader.py` - Story data caching
  - `models.py` - ResultDataset, ComparisonDataset, MaxMinDataset

**Import System:**
- `services/import_preparation.py` - Headless prescan service (file discovery, load case extraction)
  - `ImportPreparationService` - Folder/file scanning with parallel execution
  - `PrescanResult` / `FilePrescanSummary` - Prescan data models
  - `detect_conflicts()` - Conflict detection logic
  - `determine_allowed_load_cases()` - Load case filtering
- `processing/enhanced_folder_importer.py` - Enhanced import with conflict resolution
- `processing/folder_importer.py` - Basic folder import
- `processing/data_importer.py` - Single-file import
- `processing/selective_data_importer.py` - Load case filtering
- `processing/excel_parser.py` - Excel sheet parsing
- `processing/result_transformers.py` - Data transformation (Excel → ORM)
- `processing/pushover_parser.py` - Pushover curve Excel parser (v2.10)
- `processing/pushover_global_parser.py` - Pushover global results parser (v2.11)
- `processing/pushover_soil_pressure_parser.py` - Pushover soil pressures parser (v2.13)
- `processing/pushover_vert_displacement_parser.py` - Pushover vertical displacements parser (v2.13)
- `processing/pushover_joint_parser.py` - Pushover joint displacements parser (v2.13)
- `processing/pushover_global_importer.py` - Pushover global results importer (v2.11)
- `processing/pushover_soil_pressure_importer.py` - Pushover soil pressures importer (v2.13)
- `processing/pushover_vert_displacement_importer.py` - Pushover vertical displacements importer (v2.13)
- `processing/pushover_joint_importer.py` - Pushover joint displacements importer (v2.13)

**UI:**
- `gui/project_detail/` - Project detail window package (window.py, view_loaders.py, event_handlers.py)
- `gui/project_detail_window.py` - Re-exports from gui.project_detail (backward compat)
- `gui/tree_browser/` - Results tree browser package (decomposed v2.19)
  - `browser.py` - Main ResultsTreeBrowser class
  - `nltha_builders.py` - NLTHA section tree builders
  - `pushover_builders.py` - Pushover section tree builders
  - `comparison_builders.py` - Comparison set tree builders
  - `click_handlers.py` - Item click event handlers
- `gui/results_tree_browser.py` - Re-exports from gui.tree_browser (backward compat)
- `gui/result_views/standard_view.py` - Reusable table+plot
- `gui/result_views/comparison_view.py` - Multi-series comparison view
- `gui/result_views/pushover_curve_view.py` - Pushover curve visualization (NEW in v2.10)
- `gui/comparison_set_dialog.py` - Create comparison dialog
- `gui/maxmin_drifts_widget.py` - Max/Min visualization
- `gui/export/` - Export dialog package (dialogs.py, workers.py)
- `gui/export_dialog.py` - Re-exports from gui.export (backward compat)
- `gui/styles.py` - Design system constants

**Utilities:**
- `utils/color_utils.py` - Gradient colors (includes orange_blue reversed scheme)
- `utils/plot_builder.py` - Declarative plotting
- `utils/data_utils.py` - Parsing/formatting
- `utils/pushover_utils.py` - Pushover utilities (shorthand mapping, direction detection)

---

## Troubleshooting

**"No such table"**: `pipenv run alembic upgrade head`
**Import fails**: Check sheet names (case-sensitive): "Story Drifts", "Pier Forces", etc.
**Dark title bar**: Requires Windows 10+ (WSL shows light bar - expected)
**Cache issues**: Delete `src/**/__pycache__` and restart

---

## Platform Notes

**Target**: Windows 10/11
**Development**: Windows recommended (full dark theme support)
**Deployment**: Standalone .exe via PyInstaller

---

## Recent Changes (November-December 2024)

### v2.19 - ResultsTreeBrowser Decomposition (Dec 8)
- **Tree Browser Package**: Split monolithic `results_tree_browser.py` (2,413 lines) into focused modules
  - Created `gui/tree_browser/` package with 5 files
  - `browser.py` - Main ResultsTreeBrowser class with UI setup (~200 lines)
  - `nltha_builders.py` - NLTHA section tree builders (~600 lines)
  - `pushover_builders.py` - Pushover section tree builders (~500 lines)
  - `comparison_builders.py` - Comparison set tree builders (~400 lines)
  - `click_handlers.py` - Item click event handlers (~300 lines)
- **Backward Compatibility**: Original `results_tree_browser.py` re-exports ResultsTreeBrowser
  - Existing imports continue to work unchanged
  - New code can import directly from `gui.tree_browser`
- **Code Organization**: ~2,413 lines split into logical modules
  - Builders separated by analysis type (NLTHA, Pushover, Comparison)
  - Click handlers centralized in dedicated module
  - Main browser class focuses on delegation

### v2.18 - ProjectDetailWindow Decomposition (Dec 8)
- **Project Detail Package**: Split monolithic `project_detail_window.py` (1,983 lines) into focused modules
  - Created `gui/project_detail/` package with 4 files
  - `window.py` - Main window class with UI setup (~600 lines)
  - `view_loaders.py` - 20+ data loading functions (~600 lines)
  - `event_handlers.py` - Browser selection event handlers (~250 lines)
  - `__init__.py` - Package exports
- **Backward Compatibility**: Original `project_detail_window.py` re-exports ProjectDetailWindow
  - Existing imports continue to work unchanged
  - New code can import directly from `gui.project_detail`
- **Code Organization**: ~1,983 lines split into logical modules
  - View loaders handle data fetching and display
  - Event handlers process browser selection changes
  - Window class focuses on UI structure and delegation

### v2.17 - Export Dialog Decomposition (Dec 8)
- **Export Package**: Split monolithic `export_dialog.py` (1,551 lines) into focused modules
  - Created `gui/export/` package with 3 files
  - `dialogs.py` - 3 dialog classes (Comprehensive, Simple, ProjectExcel)
  - `workers.py` - 3 worker thread classes for background export operations
  - `__init__.py` - Package exports for clean imports
- **Backward Compatibility**: Original `export_dialog.py` re-exports all classes
  - Existing imports continue to work unchanged
  - New code can import directly from `gui.export`
- **Code Organization**: ~1,551 lines split into logical modules
  - Dialogs handle UI and user interaction
  - Workers handle background thread operations
  - Clear separation between UI and processing

### v2.16 - Repository Decomposition (Dec 7)
- **Repository Package**: Split monolithic `repository.py` (1,078 lines) into focused modules
  - Created `database/repositories/` package with 8 specialized files
  - `project.py` - Project operations
  - `load_case.py` - Load case operations
  - `story.py` - Story and story-level result operations (drifts, forces, etc.)
  - `result_set.py` - Result set and comparison set operations
  - `element.py` - Element operations
  - `cache.py` - All cache repositories (Global, Element, Joint, MaxMin)
  - `foundation.py` - Soil pressure and vertical displacement operations
  - `pushover.py` - Pushover case operations
- **Backward Compatibility**: Original `repository.py` re-exports all classes
  - Existing imports continue to work unchanged
  - New code can import directly from `database.repositories`
- **Code Organization**: ~1,078 lines split into logical, focused modules
  - Each file handles one domain area
  - Easier to navigate and maintain
  - Clear separation of concerns

### v2.15 - Architecture Cleanup (Dec 7)
- **Code Deduplication**: Consolidated pushover direction detection across 6 parsers
  - Shared `detect_direction()` function in `utils/pushover_utils.py`
  - Eliminated ~200 lines of duplicated code
  - Additional utilities: `preserve_order()`, `restore_categorical_order()`
- **LRU Cache Eviction**: Added memory management to data providers
  - `LRUCache` class with configurable max size (default: 100 entries)
  - Oldest entries automatically evicted when over capacity
  - Configurable via `RPS_MAX_CACHE_SIZE` environment variable
  - Applied to all three providers: Standard, Element, Joint
- **Circular Dependency Fix**: Fixed processing → gui import cycle
  - `enhanced_folder_importer.py` now uses lazy imports for dialog classes
  - GUI dialogs imported only when needed, not at module load
- **Debug Logging**: Replaced print statements with proper logging
  - 9 debug prints converted to `logger.debug()` in `database/base.py`
  - Follows Python logging best practices
- **Dead Code Removal**: Cleaned up unused files
  - Deleted `gui/main_window.py.bak` (backup file)
  - Deleted `gui/visualization_widget.py` (placeholder with only TODOs)
- **Package Organization**: Added missing `__init__.py` files
  - Created `gui/components/__init__.py` for component exports
  - Created `gui/tree_browser/__init__.py` for future decomposition
- **Class Naming**: Fixed duplicate class name collision
  - Renamed `PushoverImportWorker` → `PushoverCurveImportWorker` in `pushover_import_dialog.py`
- **Test Coverage**: Added tests for new functionality
  - `test_lru_cache.py` - LRU cache behavior tests
  - Extended `test_project_detail_controllers.py` with SelectionState tests
  - Test count: 63 → 76 tests (all passing)

### v2.14 - Context-Aware Export System (Dec 2)
- **Fully Independent Export**: NLTHA and Pushover exports are completely separated
  - Export dialog filters result sets by `analysis_type` attribute
  - NLTHA context shows only NLTHA result sets (where `analysis_type != 'Pushover'`)
  - Pushover context shows only Pushover result sets (where `analysis_type == 'Pushover'`)
  - Result type discovery queries across ALL result sets of the selected analysis type
- **Pushover Curve Export**: Integrated curves export into comprehensive export dialog
  - "Curves" checkbox appears only in Pushover context
  - Export curves only, results only, or both curves + results
  - Combined mode: All curves in single Excel file with separate sheets per case
  - Per-file mode: One Excel file per result set with sheets for each pushover case
  - CSV not supported for curves (requires multi-sheet format)
- **Smart Context Switching**: Export button behavior based on active tab
  - NLTHA tab → `ComprehensiveExportDialog` with `analysis_context='NLTHA'`
  - Pushover tab → `ComprehensiveExportDialog` with `analysis_context='Pushover'`
  - Window titles and labels dynamically update based on context
- **Error Handling**: Shows warning dialog if no result sets exist for selected context
- **UI Improvements**:
  - Info label shows: "Found X NLTHA result set(s) with Y result type(s)"
  - Export workers handle curve export alongside global/element/joint results
  - Progress tracking for all export types including curves
- **File Locations**:
  - Dialog: `gui/export_dialog.py` (lines 25-1001)
  - Context switching: `gui/project_detail_window.py` (lines 2088-2150)
  - Worker threads: `gui/export_dialog.py` (lines 720-1001)

### v2.13 - Pushover Joints Support (Dec 1)
- **Pushover Foundation Results**: Complete joints support for pushover analysis
  - Soil Pressures parser and importer using "Soil Pressures" sheet
  - Vertical Displacements parser using "Fou" + "Joint Displacements" sheets
  - Joint Displacements (Ux, Uy, Uz) from "Joint Displacements" sheet
  - All three types automatically imported with global results (no separate dialog)
- **Parser Implementation**: Three new parsers following NLTHA pattern
  - `PushoverSoilPressureParser` - Min soil pressure per foundation element
  - `PushoverVertDisplacementParser` - Min Uz for foundation joints (filtered by Fou sheet)
  - `PushoverJointParser` - Already existed, now integrated into global import
  - Direction filtering using regex: `{direction}[+-]?` for pushover cases
  - Preserves Excel order using `.unique()` and Pandas Categorical
- **Importer Integration**: Added to `PushoverGlobalImportDialog` worker thread
  - Soil pressures: 85-90% of import progress (after global results)
  - Vertical displacements: 90-95% of import progress
  - Joint displacements: 85% of import progress (alongside global)
  - All use same X/Y load case selection as global results
- **Result Type Naming**: Critical `_Min` suffix for cache storage
  - `"SoilPressures_Min"` stored in JointResultsCache (not `"SoilPressures"`)
  - `"VerticalDisplacements_Min"` stored in JointResultsCache (not `"VerticalDisplacements"`)
  - Mismatch between importer and view will prevent data display
  - Tree browser checks for `_Min` suffix when showing sections
- **Tree Browser Updates**: New Joints category at same level as Curves/Global/Elements
  - `_add_pushover_soil_pressures_section()` - Plot + Table views
  - `_add_pushover_vertical_displacements_section()` - Plot + Table views
  - `_add_pushover_joint_displacements_section()` - Ux, Uy, Uz table views (already existed)
  - Click handlers emit to existing soil pressure/vertical displacement views (reused from NLTHA)
- **Data Flow**: Foundation joint list from Fou sheet
  - Vertical displacements filtered to only joints in Fou sheet (e.g., 953 joints)
  - Soil pressures use all foundation elements (e.g., 720 elements)
  - Joint displacements include all joints (not filtered by Fou)
- **View Reuse**: Uses existing NLTHA joint views
  - `load_all_soil_pressures()` - Scatter plot widget
  - `load_soil_pressures_table()` - Wide-format table in beam_rotations_table widget
  - `load_all_vertical_displacements()` - Scatter plot widget
  - `load_vertical_displacements_table()` - Wide-format table
  - Load case shorthand mapping applied to all joint result tables
- **Test Results**: Validated with 711Vic_Push_DES_All.xlsx
  - Soil Pressures: 720 elements × 2 load cases (Push Modal X, Push Uniform X)
  - Vertical Displacements: 953 joints × 2 load cases (filtered by Fou sheet)
  - Joint Displacements: All joints with Ux, Uy, Uz components
  - All parsers and importers tested successfully
- **File Locations**:
  - Parsers: `processing/pushover_soil_pressure_parser.py`, `pushover_vert_displacement_parser.py`
  - Importers: `processing/pushover_soil_pressure_importer.py`, `pushover_vert_displacement_importer.py`
  - Dialog: `gui/pushover_global_import_dialog.py` (lines 208-246)
  - Tree: `gui/results_tree_browser.py` (lines 1717-1737, 2258-2342)

### v2.12 - Pushover Load Case Mapping & UX Improvements (Nov 26)
- **Load Case Shorthand Mapping**: Automatic shorthand names for pushover load cases
  - Long names like `Push-Mod-X+Ecc+` displayed as `Px1`, `Py1`, etc. in table headers
  - Plot legends show full mapping: `"Px1 = Push-Mod-X+Ecc+"`
  - Reduces visual clutter and improves readability for 16+ load cases
  - Mapping created once per result set and cached in memory
  - Location: `utils/pushover_utils.py`, `project_detail_window.py:582-640`
- **Dual-Format Support**: Handles both hyphen and underscore naming conventions
  - Global results use hyphens: `Push-Mod-X+Ecc+`
  - Element results use underscores: `Push_Mod_X+Ecc+`
  - Regex pattern preserves +/- eccentricity signs: `(?<!Ecc)-(?!Ecc)`
  - Extended mapping includes both variants (32 entries from 16 base cases)
- **Automatic Context Switching**: App detects pushover result sets automatically
  - Checks `ResultSet.analysis_type` attribute when navigating tree
  - Switches to "Pushover" context for pushover result sets
  - Switches to "NLTHA" context for non-pushover result sets
  - No manual tab clicking required
  - Location: `project_detail_window.py:658-677`
- **Fixed Column/Beam Click Handlers**: Added missing event handlers for pushover elements
  - `pushover_column_result` handler for R2/R3 column rotations
  - `pushover_beam_result` handler for beam rotations
  - Properly extracts `ColumnRotations` from `ColumnRotations_R2` suffix
  - Location: `results_tree_browser.py:1557-1575`
- **Mapping Application**: Shorthand applied to all result sections
  - Standard view (global results, element results, joint results)
  - Wide-format tables (beam rotations, soil pressures, vertical displacements)
  - Comparison views (preserved for future implementation)
  - Error handling with graceful fallback to original headers

### v2.11 - Pushover Global Results (Nov 23)
- **Pushover Global Results Import**: Complete story-level results support
  - `PushoverGlobalImportDialog` with result set selection
  - Imports Story Drifts, Story Forces, Floor Displacements from folder
  - X and Y direction load case selection (separate columns)
  - **Required Workflow**: Must import curves first, then select result set for global results
  - Validation prevents import if no pushover result sets exist
- **Result Set Selection**: Combo box populated with existing pushover result sets
  - Replaces text input that defaulted to "Pushover_Global"
  - Ensures global results are associated with correct curve result set
  - Warning dialog if curves haven't been imported yet
- **Parser Direction Filtering**: Fixed Excel direction column interpretation
  - Direction column = drift/force COMPONENT (X or Y), not pushover direction
  - Pushover direction from Output Case NAME using regex: `[_/]{direction}[+-]`
  - All pushover cases report both X and Y components (primary + cross)
  - Filters correctly to get only relevant cases per direction
- **Story Order Preservation**: Matches NLTHA pattern for correct building profile display
  - Uses `df['Story'].unique().tolist()` to preserve Excel first-occurrence order
  - `groupby(..., sort=False)` prevents alphabetical sorting
  - Restores order after groupby using Pandas Categorical
  - Stores `story_sort_order` per record (0-based Excel row index)
- **Cache Build Fix**: Added `session.flush()` before cache building
  - Critical fix: Ensures all imported records are written to database
  - Cache query was running before records were flushed, causing incomplete cache
  - Now all stories and directions appear correctly in cache
- **Tree Browser Structure**: Global Results at same level as Curves
  ```
  └── Result Set (e.g., "160Will_Push")
      ├── Curves
      │   ├── X Direction
      │   └── Y Direction
      └── Global Results
          ├── Story Drifts (X, Y)
          ├── Story Forces (X, Y)
          └── Floor Displacements (X, Y)
  ```
- **Load Case Name Handling**: Replaces underscores with hyphens
  - Prevents transformer from incorrectly splitting on underscores
  - `Push_Mod_X+Ecc+` becomes `Push-Mod-X+Ecc+` in cache
  - Direction suffix appended: `Push-Mod-X+Ecc+_X` for X drifts

### v2.10 - Pushover Curve Visualization (Nov 22)
- **Pushover Curve Visualization**: Complete pushover capacity curve support
  - `PushoverCurveView` widget with table + plot layout
  - Horizontal splitter: table (auto-sized) left, plot (stretch) right
  - 3-column table: Step | Base Shear (kN) | Displacement (mm)
  - Auto-sizing: Table calculates exact height after data loads
  - Plot: Displacement X-axis, Base Shear Y-axis, range from (0,0) with 5% padding
- **Pushover Parser**: Excel file parsing for capacity curves
  - `PushoverParser` class extracts displacement and shear data
  - Parses "Joint Displacements" sheet for displacement curves
  - Parses "Story Forces" sheet for base shear (filtered by base story + bottom location)
  - Normalizes displacements (zero initial value, absolute values)
  - Merges data by matching step numbers
  - Returns `PushoverCurveData` container objects
- **Table Border Fix**: Eliminated double borders project-wide
  - Set `QTableWidget.setFrameShape(QFrame.Shape.NoFrame)` on all tables
  - Native frame disabled, CSS border only (`border: 1px solid #2c313a`)
  - Applied to `PushoverCurveView` and `ResultsTableWidget`
  - Clean single border with no layering artifacts
- **Direction Support**: Automatically detects X/Y direction from case names
- **Styling Consistency**: Matches NLTHA results (dark theme, teal accent, no rounded corners)

### v2.9 - Database Connection Management & UX Improvements (Nov 15)
- **Database Connection Fix**: Comprehensive solution for Windows file locking issues
  - Implemented engine registry with `NullPool` to eliminate connection pooling
  - `dispose_project_engine()` function explicitly closes all database connections
  - Project detail windows now dispose engines on close
  - Delete operation disposes engines before file deletion
  - Eliminates "process cannot access file" errors on project deletion
- **Import Dialog Enhancement**: Fixed premature button activation
  - Start Import button now disabled during file scanning
  - Button state properly tracked through scan lifecycle
  - Prevents import attempts before scan completion
- **Project Window Management**: Single-instance windows with proper tracking
  - Prevents duplicate project detail windows
  - Existing windows brought to front when reopened
  - Automatic cleanup when windows close
  - Windows explicitly closed before project deletion
- **Navigation UI Refresh**: Modern web-style header
  - Increased navigation font size from 16px to 22px
  - Reduced vertical padding for tighter header (12px → 8px)
  - Removed underline effects for cleaner look
  - Bold weight indicates active navigation item

### v2.8 - Import System Refactor (Nov 15)
- **Service Layer Extraction**: Import prescan logic moved to `services/import_preparation.py`
  - Headless `ImportPreparationService` for reusable prescan operations
  - Parallel file scanning with `ThreadPoolExecutor` (6 workers)
  - `PrescanResult` and `FilePrescanSummary` data models
  - Pure functions for conflict detection and load case filtering
- **Provider Pattern**: Data retrieval refactored with dedicated providers
  - `StandardDatasetProvider` (global/story-based results)
  - `ElementDatasetProvider` (element-specific results)
  - `JointDatasetProvider` (foundation/joint results)
  - Each provider handles caching and invalidation independently
- **Repository Separation**: Element query logic extracted to `element_result_repository.py`
  - `ElementResultQueryRepository` - Encapsulates ORM queries for max/min datasets
  - Model registry pattern for different element types (Walls, Columns, Beams, Quads)
  - Cleaner separation between CRUD (BaseRepository) and complex queries
- **Improved Modularity**: Better separation of concerns across import/export pipeline

### v2.7 - Multi-Set Export & UI Enhancements (Nov 13)
- **Multi-Result-Set Export**: Select multiple result sets to export simultaneously
- **Joint Results Export**: Full support for exporting SoilPressures and VerticalDisplacements
- **Single Timestamp**: All files in one export operation share the same timestamp
- **Export Dialog Redesign**: Wide layout with Result Types (left) | Result Sets + Options (right)
- **Comparison Dialog**: Wide layout matching import/export style with filtered result types
- **Joint Comparison Plots**: Scatter plots for comparing soil pressures and vertical displacements across result sets
- **Blur Overlay**: Transparent blur effect when modal dialogs open

### v2.6 - Foundation Results Summary Columns (Nov 12)
- Added Average, Maximum, Minimum columns to soil pressure tables
- Added Average, Maximum, Minimum columns to vertical displacement tables
- Summary columns display in lighter gray color for distinction
- Columns appear at end: Shell Object | Unique Name | [Load Cases] | Average | Maximum | Minimum

### v2.5 - Foundation Results & Comparisons (Nov 12)
- **Soil Pressures**: Full support with table, plot, and comparison views
- **Vertical Displacements**: Full support with table, plot, and comparison views
- **Joint Comparisons**: New comparison type for foundation elements (load case vs result set)
- **Color Scheme**: Reversed gradient (orange_blue) for foundation results - lower values = orange (critical)
- **Load Case Ordering**: Lexicographic sorting for foundation result load cases
- **Multi-File Import**: Shared foundation joint list across all Excel files in folder import
- **Prescan Enhancement**: Soil pressures now detected in folder import prescan
- Foundation joints from Fou sheet propagated to all files with Joint Displacements sheet

### v2.4 - Element-Level Comparisons (Nov 11)
- Full element comparison support (walls, columns, beams)
- Individual element selection in comparison tree (P1, C5, etc.)
- V2/V3 direction support for shears in comparisons
- Element comparison titles: "P1 - WallShears V2 - DES vs MCE Comparison"
- Fixed parameter order bug in `build_element_comparison`

### v2.3 - Comparison View Design (Nov 11)
- Custom comparison plot widget without tabs
- Rounded card-style legend on right side with color indicators
- Ratio columns (last/first) instead of delta: "MCE/DES = 1.68"
- Table formatting: centered values, % for drifts only, 2-decimal ratios
- Dynamic table width (no scrolling), plot takes remaining space
- Improved titles: "Drifts X - DES vs MCE Comparison"

### v2.2 - Export Dialog Refinement (Nov 10)
- Fixed window height: `setMinimumWidth(750)` instead of `setMinimumSize(750, 400)`
- Reduced spacing: 8px layout spacing, 8px top margin
- Removed reload button from project header
- Max/Min load cases now sorted lexicographically

### v2.1 - Comprehensive Export System (Nov 8)
- Auto-discovery export dialog (queries cache for available types)
- Multi-format: Combined Excel, Per-file Excel/CSV
- Shows base types, auto-expands to directions

### v2.0 - Architecture Refactor (Nov 8)
- BaseRepository pattern (~130 lines removed)
- BaseImporter hierarchy (~95 lines removed)
- Extracted reusable UI components

### v1.9.1 - Element Type Separation (Nov 7)
- Quad rotations: `element_type="Quad"` (not "Wall")
- Per-sheet conflict resolution
- Project structure cleanup

---

**Last Updated**: 2024-12-07
**Version**: 2.16
