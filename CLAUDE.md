# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Quick Reference

**Documentation Structure:**
- **This file (CLAUDE.md)**: Quick development guide and common tasks
- **[ARCHITECTURE.md](ARCHITECTURE.md)**: Complete technical architecture, data model, patterns
- **[PRD.md](PRD.md)**: Product requirements, features, roadmap
- **[DESIGN.md](DESIGN.md)**: Visual design system, styling guidelines, component patterns

---

## Project Overview

**Results Processing System (RPS)** - Desktop application for processing and visualizing structural engineering results from ETABS/SAP2000 Excel exports.

**Status**: Production-ready with refactored, extensible architecture

**Tech Stack**: PyQt6 + PyQtGraph + SQLite + SQLAlchemy + Pandas

---

## Current State - November 2025

### ✅ Fully Implemented

**Core Features:**
- ✅ Hybrid normalized + wide-format cache data model
- ✅ Hierarchical data organization (Result Sets → Categories → Results)
- ✅ Folder-based batch import with progress tracking
- ✅ Single-file import with validation
- ✅ Project detail view: Browser | Table | Plot (3-panel)
- ✅ Story drifts visualization with interactive column selection
- ✅ Max/Min drifts visualization with separate plot/table views
- ✅ Modern minimalist design system (Vercel/Linear inspired)
- ✅ Hot-reload development environment

**Data Hierarchy (100% Complete):**
- ✅ Result sets with user-defined names (DES, MCE, SLE, etc.)
- ✅ Load cases shared across all result sets
- ✅ Result categories: Envelopes → Global Results → Elements (Walls, Columns, Beams)
- ✅ **Global Results**: Drifts, Accelerations, Forces, Displacements (all with Max/Min)
- ✅ **Element Results**:
  - Wall Shears (V2/V3), Quad Rotations (per-pier data)
  - Column Shears (V2/V3), Column Axials (Min), Column Rotations (R2/R3)
  - Beam Rotations (R3 Plastic)
- ✅ Full UI integration: tree browser + detail views
- ✅ Duplicate validation for result set names
- ✅ **Sheet-Specific Story Ordering**: Each result type preserves its own Excel sheet order
- ✅ Database migration with backward compatibility

**Architecture:**
- ✅ Configuration-driven transformers (~180 lines of duplication eliminated)
- ✅ Repository pattern for clean data access
- ✅ Pluggable result type system (add new types in ~10 lines)
- ✅ **Modular Service Layer**: result_service refactored into 6 focused modules
- ✅ **Per-Result Story Ordering**: story_sort_order in all result/cache tables
- ✅ **Dual Cache System**: GlobalResultsCache + ElementResultsCache
- ✅ **Directionless Results Support**: QuadRotations (no X/Y split)
- ✅ Alembic migrations for schema evolution
- ✅ **Comprehensive Testing**: Unit tests with stub/mock patterns

**Design System:**
- ✅ Modern minimalist aesthetic (documented in DESIGN.md)
- ✅ Geometric icon system (no colorful emojis)
- ✅ Transparent layers with subtle interactions
- ✅ Consistent 4px spacing grid
- ✅ Cyan accent (#67e8f9) for selections
- ✅ 14px base font size

**Interactive Features:**
- ✅ Row hover highlighting with gentle cyan overlay (8% opacity)
- ✅ Multi-row selection with toggle on click
- ✅ Column header hover feedback (cyan text + background)
- ✅ Legend-based plot interaction (hover/click on legend items)
- ✅ Gradient color preservation in all interaction states
- ✅ Manual selection system (no Qt default styling conflicts)

**Browser & Navigation (NEW - November 2025):**
- ✅ **Smart Data Detection**: Browser automatically hides result types without data
  - Queries GlobalResultsCache and ElementResultsCache on project load
  - Only shows sections (Drifts, Walls, Columns, etc.) that have imported data
  - Reduces clutter when partial data sets are loaded
- ✅ **Optimized Default View**: Hierarchical expansion states for quick overview
  - Global and Elements sections: Expanded (shows result type names)
  - Result types (Drifts, Forces, etc.): Collapsed (hides directions)
  - Element categories (Walls, Columns, Beams): Collapsed (hides piers/subcategories)
- ✅ **Compact Layout Optimization**: Space-efficient UI for smaller screens
  - Standard views: 60/40 table/plot split with 10px table font
  - Legend positioned below plots in multi-row grid layout
  - Max/Min tables: Ultra-compact (7px font, minimal padding)
  - Plot titles removed to maximize visualization space

### 🎯 Next Steps

**Near-term (Ready to implement):**
- [ ] Accelerations visualization (config exists, just load UX data)
- [ ] Forces visualization (config exists, just load VX data)
- [ ] Displacements visualization (new result type)
- [ ] Export functionality (CSV, Excel, plots to PNG/PDF)
- [ ] Multi-result-set comparison view

**Future Enhancements:**
- [ ] Time-series results support (placeholder in UI exists)
- [ ] Additional element results (spandrels)
- [ ] Joint results (displacements, reactions)
- [ ] 3D model visualization
- [ ] Custom report generation

**Recently Completed (October-November 2025):**
- ✅ **Result Service Modularization** (Nov 2025): Refactored into 6 focused modules with comprehensive tests
- ✅ **Smart Data Detection** (Nov 2025): Browser automatically hides empty result type sections
- ✅ **Browser UX Optimization** (Nov 2025): Configurable expansion states for streamlined navigation
- ✅ **Layout Optimization** (Nov 2025): Responsive layouts optimized for smaller screens
- ✅ Wall Shears element results (V2/V3 directions, per-pier)
- ✅ Quad Rotations element results (directionless, percentage display)
- ✅ Column Shears element results (V2/V3 directions, per-column)
- ✅ Column Minimum Axial forces (per-column)
- ✅ Column Rotations (R2/R3 plastic hinges, from Fiber Hinge States)
- ✅ Beam Rotations (R3 plastic hinges, from Hinge States)
- ✅ Max/Min support for all element results
- ✅ **All Rotations scatter plots** (combines all elements, story bins with jitter)
- ✅ **Wide-format tables** for beam rotations (load cases as columns, with Avg/Max/Min)
- ✅ **Story Ordering System**: Sheet-specific ordering for most results, global Story.sort_order for quad rotations
- ✅ Directionless result type support (single plot/table, no X/Y split)
- ✅ **Gradient color formatting** for all tables (value-based colors with center alignment)
- ✅ **UI View Pattern**: StandardResultView component with view orchestration

---

## Architecture Overview

> **📐 Full Architecture**: See [ARCHITECTURE.md](ARCHITECTURE.md)
> **🎨 Design System**: See [DESIGN.md](DESIGN.md)
> **📋 Product Requirements**: See [PRD.md](PRD.md)

**Key Principles:**
- **Configuration-Driven**: Result types defined in `config/result_config.py` (~10 lines per type)
- **Pluggable Transformers**: Strategy pattern for data processing (`processing/result_transformers.py`)
- **Hybrid Data Model**: Normalized tables + wide-format cache for performance
- **Component-Based UI**: Signal/slot communication between table and plot widgets

**Quick Reference:**
- Data model and schema: [ARCHITECTURE.md Section 4](ARCHITECTURE.md#4-data-architecture)
- Configuration system: [ARCHITECTURE.md Section 5](ARCHITECTURE.md#5-configuration-system)
- Transformer pattern: [ARCHITECTURE.md Section 6](ARCHITECTURE.md#6-transformer-system)
- UI architecture: [ARCHITECTURE.md Section 8](ARCHITECTURE.md#8-ui-architecture)
- Result service architecture: [ARCHITECTURE.md Section 9.5](ARCHITECTURE.md#95-result-service-architecture)
- Extension points: [ARCHITECTURE.md Section 10](ARCHITECTURE.md#10-extension-points)

---

## Development Commands

### Setup & Run
```bash
pipenv install --dev                    # Install dependencies
pipenv run alembic upgrade head         # Create database tables
pipenv run python src/main.py           # Run application
pipenv run python dev_watch.py          # Run with hot-reload
```

### Testing & Quality
```bash
pipenv run pytest tests/ -v             # Run tests
pipenv run pytest --cov=src tests/      # With coverage
pipenv run black src/                   # Format code
pipenv run flake8 src/                  # Lint code
```

### Database Migrations
```bash
pipenv run alembic revision --autogenerate -m "Description"
pipenv run alembic upgrade head
pipenv run alembic downgrade -1
```

### Building
```bash
pipenv run pyinstaller src/main.py --onefile --windowed --name RPS
```

---

## Common Development Tasks

### Adding a New Result Type

> **📐 See**: [ARCHITECTURE.md Section 10](ARCHITECTURE.md#10-extension-points) for complete example

**Quick steps** (~10 minutes):
1. Add config to `config/result_config.py` (~5 lines)
2. Add transformer to `processing/result_transformers.py` (~10 lines)
3. Register transformer in `TRANSFORMERS` dict
4. Load data into cache via import

**Done!** Table, plot, colors, and formatting work automatically.

---

### Modifying Table Colors

```python
# config/result_config.py - Change color scheme
RESULT_CONFIGS['Drifts'].color_scheme = 'green_red'

# utils/color_utils.py - Add custom scheme
COLOR_SCHEMES['custom'] = ('#3b82f6', '#ff4757')
```

---

### Modifying Plot Appearance

```python
# utils/plot_builder.py - Change builder defaults

# Plot padding (current: small margins for tight fit)
def set_value_range(self, min_val, max_val, left_padding=0.03, right_padding=0.05):
    # Both normal and min/max drifts use 3% left, 5% right padding
    ...

def set_story_range(self, num_stories, padding=0.02):
    # 2% padding on vertical axis for all plots
    ...

# Tick spacing (dynamic with 1-2-5 pattern, capped at 0.5)
def set_dynamic_tick_spacing(self, axis='bottom', min_val=None, max_val=None, num_intervals=6):
    # Targets 6 intervals, rounds to nice numbers: 0.1, 0.2, 0.5 (max)
    # Never exceeds 0.5 interval spacing for drift values
    ...

# results_plot_widget.py - Adjust plot-specific logic
def _plot_building_profile(self, df, result_type):
    # Change line styles, colors, etc.
    ...
```

---

### Styling New UI Components

**Follow the design system** documented in [DESIGN.md](DESIGN.md):

```python
# Use modern minimalist style
QWidget {
    background-color: transparent;  # Start transparent
    font-size: 14px;                # Standard text size
    color: #9ca3af;                 # Muted gray default
}

QWidget:hover {
    background-color: rgba(255, 255, 255, 0.03);  # Subtle hover
    color: #d1d5db;                                # Lighter on hover
}

QWidget:selected {
    background-color: rgba(74, 125, 137, 0.12);  # Subtle accent
    color: #67e8f9;                               # Cyan for selection
}
```

**Icon System** - Use geometric shapes (see DESIGN.md):
- Navigation: `▸ ◆ ◇ ›`
- Actions: `⊕ ⊖ ✓ ✗ ⚠`
- States: `└ ├ │ ⓘ`

**Color Palette**:
- Background: `#0a0c10` (primary), `#161b22` (secondary)
- Text: `#d1d5db` (primary), `#9ca3af` (secondary)
- Accent: `#4a7d89` (teal), `#67e8f9` (cyan)
- Border: `#2c313a`

**Spacing**: Use 4px increments (`4px, 8px, 12px, 16px, 24px`)

---

### Implementing Table Interactions

**Manual Selection System** (no Qt default styling conflicts):

```python
# Disable Qt's default selection
table.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
table.setFocusPolicy(Qt.FocusPolicy.NoFocus)

# Enable mouse tracking
table.setMouseTracking(True)
table.viewport().setMouseTracking(True)

# Track state manually
table._hovered_row = -1
table._selected_rows = set()

# Install event filter for hover
table.viewport().installEventFilter(self)

# Connect signal for click
table.cellClicked.connect(self._on_cell_clicked)
```

**Preserving Gradient Colors**:

```python
# Store original color when creating items
gradient_color = get_gradient_color(value, min_val, max_val, 'blue_orange')
item.setForeground(gradient_color)
item._original_color = QColor(gradient_color)  # Store a COPY

# Restore original color in all states
def _apply_row_style(self, table, row):
    for col in range(table.columnCount()):
        item = table.item(row, col)
        if item and hasattr(item, '_original_color'):
            # Always restore original color first
            item.setForeground(item._original_color)
            # Then apply background overlay
            if is_hovered or is_selected:
                item.setBackground(QColor(103, 232, 249, 20))  # 8% opacity
```

**Key Points**:
- Store QColor copies, not references (prevents mutation)
- Use `cellClicked` signal instead of MouseButtonPress events
- Apply background overlays only, never modify foreground colors
- Event filter handles hover, signal handles click

---

### Creating Reusable View Components

**View Pattern** (extracted from `project_detail_window.py`):

The `StandardResultView` pattern combines table + plot in a reusable component:

```python
# gui/result_views/standard_view.py
class StandardResultView(QWidget):
    """Reusable table+plot component with automatic signal wiring."""

    def __init__(self):
        self.table = ResultsTableWidget()
        self.plot = ResultsPlotWidget()

        # Configure horizontal splitter
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.addWidget(self.table)
        splitter.addWidget(self.plot)

        # Connect signals automatically
        self.table.selection_changed.connect(self.plot.highlight_load_cases)
        self.table.load_case_hovered.connect(self.plot.hover_load_case)
        self.table.hover_cleared.connect(self.plot.clear_hover)

    def set_dataset(self, dataset: ResultDataset):
        """Load data into both table and plot."""
        self.table.load_dataset(dataset)
        self.plot.load_dataset(dataset)

    def clear(self):
        """Reset both components."""
        self.table.clear_data()
        self.plot.clear_plots()
```

**Usage in ProjectDetailWindow**:
```python
# Create once in __init__
self.standard_view = StandardResultView()

# Show/hide based on result type
if result_type.startswith("MaxMin"):
    self.standard_view.hide()
    self.maxmin_widget.show()
else:
    self.standard_view.show()
    self.maxmin_widget.hide()

# Load data
dataset = self.result_service.get_standard_dataset(result_type, direction, result_set_id)
self.standard_view.set_dataset(dataset)
```

**Benefits**:
- Single source of truth for table+plot layout
- Consistent signal wiring across views
- Easy to add new view types (just create new widget, add to window)
- Reduces code duplication

---

### Adding Database Columns

> **📐 See**: [ARCHITECTURE.md Section 12](ARCHITECTURE.md#12-development-patterns) for details

```bash
# 1. Edit models.py (add new Column)
# 2. Generate migration
pipenv run alembic revision --autogenerate -m "Add new_field"
# 3. Review migration file
# 4. Apply migration
pipenv run alembic upgrade head
```

---

### Managing Projects (Catalog Tools)

> **📐 See**: [ARCHITECTURE.md Section 12](ARCHITECTURE.md#12-development-patterns) for details

```bash
# List all projects with metadata
pipenv run python scripts/project_tools.py list

# Delete project (interactive confirmation)
pipenv run python scripts/project_tools.py delete --name "ProjectName"

# Delete project (force, no confirmation)
pipenv run python scripts/project_tools.py delete --name "ProjectName" --force
```

---

### Modifying UI Components

**GMP Design System Colors:**
```python
# gui/styles.py
COLORS = {
    'background': '#0a0c10',
    'card': '#161b22',
    'accent': '#4a7d89',  # Change this
}
```

**Creating Styled Components:**
```python
# gui/ui_helpers.py
button = create_styled_button("Save", "primary", "md")
label = create_styled_label("Title", "header")
```

---

## Quick File Reference

> **📐 Complete structure**: See [ARCHITECTURE.md Section 3](ARCHITECTURE.md#3-project-structure)

**Most frequently edited files:**
- `src/config/result_config.py` - Result type definitions
- `src/config/visual_config.py` - Colors, styling, constants
- `src/processing/result_transformers.py` - Data processing logic
- `src/gui/styles.py` - GMP design system
- `src/gui/project_detail_window.py` - Main 3-panel layout
- `src/utils/color_utils.py` - Gradient color schemes
- `src/utils/plot_builder.py` - Declarative plot API

---

## Utility Functions Quick Reference

> **📐 See**: [ARCHITECTURE.md Section 7](ARCHITECTURE.md#7-utility-systems) for complete API

**Color Utilities** (`utils/color_utils.py`):
```python
from utils.color_utils import get_gradient_color
color = get_gradient_color(value, min_val, max_val, 'blue_orange')
```

**Data Utilities** (`utils/data_utils.py`):
```python
from utils.data_utils import parse_percentage_value, format_value
numeric = parse_percentage_value("1.23%")  # → 1.23
formatted = format_value(1.234, 2, '%')    # → "1.23%"
```

**Plot Builder** (`utils/plot_builder.py`):
```python
from utils.plot_builder import PlotBuilder
builder = PlotBuilder(plot_widget, config)
builder.setup_axes(story_names)
builder.add_line(x_values, y_values, color='#3b82f6', width=2)
```

---

## Platform Notes

**Target**: Windows 10/11 (primary users)

**Development**:
- Can develop on WSL/Linux
- **Recommended**: Develop on Windows for full dark theme
- Dark title bar uses Windows DWM API (Windows-only)
- On WSL/Linux: Light title bar is expected (X11 limitation)

**Deployment**: Standalone .exe via PyInstaller

---

## Known Limitations

- Only X/UX/VX directions implemented (Y directions ready, need UI)
- No time-series visualization yet
- No 3D model integration yet
- Single-user desktop app (no collaboration)
- Element results currently limited to Walls (piers) - columns, beams, spandrels ready for future implementation

> **Full constraints and assumptions**: See [PRD.md Section 7](PRD.md#7-constraints-and-assumptions)

---

## Troubleshooting

### "No such table" Error
```bash
pipenv run alembic upgrade head
```

### Import Fails
- Check sheet names (case-sensitive):
  - Global: "Story Drifts", "Story Accelerations", "Story Forces"
  - Elements: "Pier Forces", "Quad Strain Gauge - Rotation"
- Verify column format:
  - Global: `<prefix>_<load_case>_<direction>`
  - Elements: Pier-specific formats (see Excel parser)
- Test with samples in `Typical Input/`

### Dark Title Bar Not Working
- Requires Windows 10 (build 19041+) or Windows 11
- On WSL/Linux: Expected behavior (X11 limitation)
- Test on actual Windows to see dark title bar

### Hot-Reload Not Working
```bash
# Check watchfiles is installed
pipenv install watchfiles

# Restart dev server
pipenv run python dev_watch.py
```

### Pandas SettingWithCopyWarning
```python
# Always use .copy() when filtering DataFrames
def filter_columns(self, df):
    filtered = df[columns]
    return filtered.copy()  # Add .copy()
```

### Database Naming Migration
**New projects** automatically use the new naming scheme: `data/projects/{slug}/{slug}.db`

**Existing projects** with old `project.db` naming can be migrated:
```bash
# Close the RPS application first!
pipenv run python scripts/migrate_database_names.py
```

This will rename all `project.db` files to `{slug}.db` and update the catalog.

---

## Next Steps

**Immediate (< 1 hour each)**:
1. Add Accelerations visualization (load UX data from cache)
2. Add Forces visualization (load VX data from cache)
3. Add Y-direction support for all result types

**Short-term (1-2 days)**:
4. Implement time-series plotting
5. Add export functionality (CSV, PNG)
6. Multi-project comparison view

**Long-term (weeks)**:
7. 3D building model integration
8. Animation for time-history results
9. Custom report generation

> **Full roadmap**: See [PRD.md Section 6](PRD.md#6-future-enhancements-roadmap)

---

## Resources

**Documentation**:
- [ARCHITECTURE.md](ARCHITECTURE.md) - Complete technical design
- [PRD.md](PRD.md) - Product requirements and features
- [README.md](README.md) - Project overview

**External Docs**:
- [PyQt6](https://www.riverbankcomputing.com/static/Docs/PyQt6/)
- [PyQtGraph](https://pyqtgraph.readthedocs.io/)
- [SQLAlchemy](https://docs.sqlalchemy.org/)
- [Alembic](https://alembic.sqlalchemy.org/)

**Code References**:
- `Old_scripts/` - Legacy processing logic (reference)
- `tests/` - Unit test examples
- `Typical Input/` - Sample Excel files

---

## Key File Locations

**Format**: Use `filename.py:line_number` for easy navigation

**Configuration:**
- `config/result_config.py` - Result type definitions
- `config/visual_config.py` - Colors, styling constants, legend config

**Data Access:**
- `database/catalog_models.py` - Catalog ORM (project metadata - 1 table)
- `database/catalog_repository.py` - Catalog CRUD operations
- `database/models.py` - Per-project ORM (20 tables total)
  - **Foundation**: Project, Story, LoadCase, ResultSet, ResultCategory, Element
  - **Global Results**: StoryDrift, StoryAcceleration, StoryForce, StoryDisplacement
  - **Element Results**: WallShear, QuadRotation, ColumnShear, ColumnAxial, ColumnRotation, BeamRotation
  - **Cache**: GlobalResultsCache, ElementResultsCache, AbsoluteMaxMinDrift
  - **Future**: TimeHistoryData (placeholder)
- `database/repository.py` - Per-project data access (CacheRepository, ElementCacheRepository)
- `services/project_service.py` - Project context management

> **📐 Complete Database Schema**: See [ARCHITECTURE.md Section 4 - Complete Data Model](ARCHITECTURE.md#complete-data-model) for full field definitions, relationships, and indexes for all 21 tables

**Processing:**
- `processing/result_transformers.py` - Pluggable transformer system
- `processing/import_context.py` - ResultImportHelper (shared import utilities, _story_order tracking)
- `processing/folder_importer.py` - Batch folder import
- `processing/data_importer.py` - Single file import with cache generation
- `processing/excel_parser.py` - Excel sheet parsing (global + element results)
- `processing/result_processor.py` - Result processing logic
- `processing/result_service/` - Data retrieval service (modular package)
  - `service.py` - ResultDataService facade with caching
  - `models.py` - ResultDataset, MaxMinDataset, ResultDatasetMeta
  - `cache_builder.py` - Standard and element dataset builders
  - `maxmin_builder.py` - Max/min envelope builders
  - `metadata.py` - Display label utilities
  - `story_loader.py` - StoryProvider caching helper

**UI Components:**
- `gui/main_window.py` - Project cards view with navigation
- `gui/project_detail_window.py` - 3-panel layout orchestration (browser | content)
- `gui/results_tree_browser.py` - Hierarchical result navigation (global + elements)
- `gui/result_views/standard_view.py` - Reusable table+plot view component
- `gui/results_table_widget.py` - Table with manual selection and gradient colors
- `gui/results_plot_widget.py` - PyQtGraph building profiles
- `gui/maxmin_drifts_widget.py` - Max/Min envelope view (supports directionless results)
- `gui/all_rotations_widget.py` - Scatter plot for all rotations with story bins and jitter
- `gui/beam_rotations_widget.py` - Beam rotations visualization
- `gui/components/legend.py` - Reusable legend widgets (static + interactive)
- `gui/window_utils.py` - Platform-specific utilities (dark title bar, app ID)
- `gui/ui_helpers.py` - Styled component factories
- `gui/styles.py` - GMP design system constants

**Utilities:**
- `utils/color_utils.py` - Gradient color interpolation
- `utils/plot_builder.py` - Declarative plot API
- `utils/data_utils.py` - Parsing and formatting helpers
- `utils/slug.py` - Slug utilities for project folders

**Processing Utilities:**
- `processing/maxmin_calculator.py` - Absolute Max/Min calculations from envelope data

---

---

## Story Ordering System

### Overview
RPS implements a sophisticated story ordering system that preserves Excel sheet order for each result type:

- **Sheet-specific ordering**: Most result types preserve their exact Excel sheet row order
- **Global ordering exception**: Quad rotations use global `Story.sort_order` from Story Drifts sheet
- **Display conventions**:
  - Plots: Bottom floors at bottom (y=0), top floors at top (ascending)
  - Tables: Bottom floors first, top floors last (ascending order)

### Implementation Details

**Why sheet-specific ordering?**
Different Excel sheets may have stories in different orders:
- Story Drifts: All stories present (S4 → S3 → S2 → S1 → Base)
- Pier Forces: Per-element sheets may skip stories where pier doesn't exist
- Quad Rotations: Sorted by element/pier name lexicographically, NOT by story

**Quad Rotations Special Case:**
Quad rotation Excel sheets are sorted by pier/element name (e.g., "P1", "P10", "P2", "P3"), not by story height. Therefore:
- Individual quad rotation views use **global `Story.sort_order`** from Story Drifts sheet
- Max/Min quad rotation views use **global `Story.sort_order`**
- "All Rotations" scatter plot uses **global `Story.sort_order`**
- This ensures correct vertical building ordering despite lexicographic element sorting in Excel

**Key Code Locations:**
- `processing/result_service/service.py` - `get_element_maxmin_dataset()` - Quad rotation detection (lines ~195-204)
- `processing/result_service/cache_builder.py` - Story ordering logic in `build_element_dataset()` (lines ~109-119)
- `processing/result_service/service.py` - `get_all_quad_rotations_dataset()` - Global sort order usage (lines ~284-326)

**Database columns:**
- `Story.sort_order` - Global story order from Story Drifts sheet (0=bottom floor)
- `<result>.story_sort_order` - Per-sheet row index (0=first row in Excel)
- Cache uses appropriate ordering based on result type

---

**Last Updated**: 2025-11-02
**Status**: Production-ready with smart data detection, optimized browser UX, and responsive layouts
**Note**: Structural details moved to [ARCHITECTURE.md](ARCHITECTURE.md) - this file focuses on quick development tasks

---

## Recent Changes (November 2025)

### ✅ Smart Data Detection & Browser Optimization (v1.7)

**Data Detection System**:
- ✅ Implemented automatic result type filtering based on loaded data
- ✅ Queries `GlobalResultsCache` and `ElementResultsCache` on project load
- ✅ Browser shows only sections with imported data (Drifts, Walls, Columns, etc.)
- ✅ Conditional rendering for all element categories (Walls, Columns, Beams)
- ✅ Backward compatible - shows all sections if data detection fails

**Browser UX Optimization**:
- ✅ Configured hierarchical expansion states for streamlined navigation:
  - **Global section**: Expanded (shows Drifts, Forces, Displacements at a glance)
  - **Elements section**: Expanded (shows Walls, Columns, Beams at a glance)
  - **Result types**: Collapsed (hides X/Y directions, Max/Min subsections)
  - **Element categories**: Collapsed (hides Shears/Rotations subcategories, pier lists)
- ✅ Reduces initial visual clutter while maintaining quick access to all result types

**Layout Optimization**:
- ✅ Standard views: Adjusted splitter to 60/40 (table/plot) for better plot visibility
- ✅ Table font reduced to 10px for compact display without scrolling
- ✅ Legend repositioned below plots in multi-row grid layout (4 items per row)
- ✅ Plot titles removed to maximize visualization area
- ✅ Max/Min tables: Ultra-compact layout (7px font, 0px 1px padding) for small screens
- ✅ Responsive design ensures readability on various screen sizes

**Implementation Details**:
- `project_detail_window.py:252-289` - `_get_available_result_types()` data detection
- `results_tree_browser.py:22-33` - `_has_data_for()` backward-compatible checking
- `results_tree_browser.py:329-356` - Conditional Walls section rendering
- `results_tree_browser.py:528-560` - Conditional Columns section rendering
- `results_tree_browser.py:762-784` - Conditional Beams section rendering
- `standard_view.py:45-56` - Optimized splitter proportions and expansion states

### ✅ Result Service Modularization (v1.6)

**Service Layer Refactor**:
- ✅ Refactored monolithic `result_service.py` (1117 lines) into focused package (6 modules, ~200 lines each)
- ✅ New modular structure:
  - `service.py` - ResultDataService facade with multi-level caching
  - `models.py` - Data models (ResultDataset, MaxMinDataset, ResultDatasetMeta)
  - `cache_builder.py` - Standard and element dataset builders
  - `maxmin_builder.py` - Drift and generic max/min builders
  - `metadata.py` - Display label utilities and overrides
  - `story_loader.py` - StoryProvider for centralized story caching
- ✅ Backward compatible imports via `__init__.py` (no breaking changes)
- ✅ Comprehensive unit tests added (`test_result_data_service.py`)
- ✅ Improved testability with stub/mock patterns

**Benefits**:
- **Single Responsibility**: Each module has one clear purpose
- **Testability**: Individual components can be tested in isolation
- **Maintainability**: Smaller files easier to navigate and understand
- **Separation of Concerns**: Models, builders, and service logic cleanly separated

### ✅ UI Refactor & Architecture Improvements (v1.5)

**View Pattern Introduction**:
- ✅ New `StandardResultView` component (reusable table+plot pattern)
- ✅ View orchestration in `ProjectDetailWindow` (dynamic widget switching)
- ✅ Extracted `window_utils.py` for platform-specific utilities
- ✅ Extracted `maxmin_calculator.py` for Max/Min calculations
- ✅ New `result_views/` directory for view components

**Improved Organization**:
- ✅ Clearer separation between reusable components and specialized widgets
- ✅ Automatic signal wiring in `StandardResultView`
- ✅ Simplified `ProjectDetailWindow` (~200 lines removed)
- ✅ Better maintainability with single source of truth for layouts

**Code Quality**:
- ✅ Reduced duplication (table+plot layout defined once)
- ✅ Consistent patterns across all directional results
- ✅ Easier to add new view types (just create widget, add to orchestrator)

**What You Need to Know**:
1. **`project_detail_window.py` is now an orchestrator** - it manages multiple specialized widgets and shows/hides them based on result type
2. **`StandardResultView` is for directional results** - use this for any result type with X/Y or V2/V3 directions
3. **Create specialized widgets for unique visualizations** - like `MaxMinDriftsWidget`, `AllRotationsWidget`, etc.
4. **Window utilities are platform-specific** - dark title bar only works on Windows, gracefully ignored on Linux/Mac
5. **Signal wiring is automatic in StandardResultView** - table ↔ plot communication is handled internally

---
