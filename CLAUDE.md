# CLAUDE.md - Quick Development Guide

**RPS (Results Processing System)** - Structural engineering results processor (ETABS/SAP2000)
**Stack**: PyQt6 + PyQtGraph + SQLite + SQLAlchemy + Pandas
**Status**: Production-ready (v2.7 - November 2024 - Multi-Set Export & UI Enhancements)

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

### Export System
- **Export Results**: Multi-format (Excel/CSV), auto-discovers types from cache
- **Export Project**: Complete project export for re-import (.xlsx)
- Location: `gui/export_dialog.py`

### Import System
- **Folder Import**: Batch import with load case selection, conflict resolution
- **File Import**: Single file validation and import
- **Foundation Support**: Vertical displacements use shared foundation joint list from Fou sheet across all files
- **Soil Pressure Detection**: Automatically detects soil pressure sheets during prescan
- Location: `gui/folder_import_dialog.py`, `processing/enhanced_folder_importer.py`

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
- `database/repository.py` - Data access (all extend BaseRepository, includes JointCacheRepository)
- `services/result_service/` - Data retrieval (6 focused modules)

**Processing:**
- `processing/result_transformers.py` - Pluggable transformers
- `processing/enhanced_folder_importer.py` - Import with conflict resolution
- `processing/excel_parser.py` - Excel parsing
- `processing/result_service/comparison_builder.py` - Multi-set comparison logic

**UI:**
- `gui/project_detail_window.py` - Main 3-panel view (browser | content)
- `gui/results_tree_browser.py` - Hierarchical browser (includes comparison sets)
- `gui/result_views/standard_view.py` - Reusable table+plot
- `gui/result_views/comparison_view.py` - Multi-series comparison view
- `gui/comparison_set_dialog.py` - Create comparison dialog
- `gui/maxmin_drifts_widget.py` - Max/Min visualization
- `gui/export_dialog.py` - Export dialogs
- `gui/styles.py` - Design system constants

**Utilities:**
- `utils/color_utils.py` - Gradient colors (includes orange_blue reversed scheme)
- `utils/plot_builder.py` - Declarative plotting
- `utils/data_utils.py` - Parsing/formatting

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

## Recent Changes (November 2024)

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

**Last Updated**: 2024-11-13
**Version**: 2.7
