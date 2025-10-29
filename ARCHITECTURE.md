# Architecture Documentation
## Results Processing System (RPS)

**Version**: 1.4
**Last Updated**: 2025-10-27
**Status**: Production-ready with element results and sheet-specific ordering

---

## 1. System Overview

### Architecture Type
**Layered desktop application** with clear separation of concerns:
- **Presentation**: PyQt6 UI components
- **Business Logic**: Data processors and transformers
- **Data Access**: SQLAlchemy ORM repositories
- **Storage**: SQLite with hybrid schema

### Key Characteristics
- **Configuration-Driven**: Result types defined declaratively
- **Pluggable Transformers**: Strategy pattern for data processing
- **Hybrid Data Model**: Normalized + denormalized cache for performance
- **Component-Based UI**: Reusable widgets with signal/slot communication

---

## 2. Technology Stack

| Component | Technology | Purpose |
|-----------|-----------|---------|
| Language | Python 3.11.3 | Application logic |
| UI | PyQt6 | Desktop GUI |
| Visualization | PyQtGraph | High-performance plotting |
| Database | SQLite 3.x | Local data storage |
| ORM | SQLAlchemy 2.x | Database abstraction |
| Migrations | Alembic | Schema versioning |
| Data Processing | Pandas | Excel parsing, transformations |

---

## 3. Project Structure

```
src/
├── config/
│   └── result_config.py          # Result type configurations (dataclasses)
├── database/
│   ├── base.py                   # Per-project DB helpers / engine factory
│   ├── catalog_base.py           # Catalog engine + Base metadata
│   ├── catalog_models.py         # Catalog ORM definitions
│   ├── catalog_repository.py     # Catalog CRUD helpers
│   ├── models.py                 # Project-scoped ORM models (hybrid schema)
│   └── repository.py             # Project-scoped repositories
├── gui/
│   ├── styles.py                 # GMP design system
│   ├── main_window.py            # Project cards view + actions
│   ├── project_detail_window.py  # 3-panel layout (browser|table|plot)
│   ├── results_table_widget.py   # Compact table display
│   └── results_plot_widget.py    # PyQtGraph building profiles
├── processing/
│   ├── excel_parser.py           # Excel file reading
│   ├── result_transformers.py    # Pluggable transformers
│   ├── data_importer.py          # Single file → DB pipeline (per project)
│   └── folder_importer.py        # Batch folder → DB pipeline (context-aware)
├── services/
│   └── project_service.py        # Catalog + project context management
└── utils/
    ├── slug.py                   # Slug utilities for project folders
    ├── color_utils.py            # Gradient color interpolation
    ├── data_utils.py             # Parsing/formatting helpers
    └── plot_builder.py           # Declarative plot construction
```

---

## 4. Data Architecture

### Hybrid Data Model
- **Normalized tables**: Maintain data integrity and relationships
- **Wide-format cache**: Optimize for fast tabular display
- **Best of both worlds**: Reliable storage + high performance

### Catalog + Project Databases
- **Catalog DB (`data/catalog.db`)** tracks project metadata (name, slug, description, per-project DB path, timestamps).
- **Per-project DBs** live under `data/projects/<slug>/<slug>.db` (e.g., `data/projects/160wil/160wil.db`) and contain only that project's stories, load cases, caches, and result sets.
- **ProjectContext** (see `services/project_service.py`) is the hand-off object used by UI/dialogs and importers to ensure they always open sessions against the correct project file while transparently creating it on first use.
- **Lifecycle**: `ensure_project_context()` guarantees catalog entry + DB file, `list_project_contexts()` feeds project listings, and `delete_project_context()` removes catalog entry plus on-disk database folder (including the database file).

### Session Strategy
- UI layers never call the old global `get_session()`; instead they request `context.session()` or `context.session_factory()` to obtain SQLAlchemy sessions bound to a specific project DB.
- Import flows (`DataImporter`, `FolderImporter`) require a session factory and therefore cannot run without a resolved project context, preventing data from leaking across projects.
- Background folder imports reuse the same factory inside worker threads so commits map to the same SQLite file without threading issues.

### Shared Import/Visualization Utilities
- **ResultImportHelper (`processing/import_context.py`)** centralizes story and load-case lookups, caches ORM entities, and preserves Excel ordering for every importer.
- **visual_config (`config/visual_config.py`)** holds the canonical palette, zero-line/average styling, and table/padding constants so tables and plots use one source of truth.
- **Legend widgets (`gui/components/legend.py`)** provide reusable static and interactive entries consumed by both standard and Max/Min views for consistent hover/toggle behavior.

### Core Schema

**Projects** → **ResultSets** → **GlobalResultsCache** / **ElementResultsCache** (wide-format JSON)
**Projects** → **Stories** + **LoadCases** → **Results** (normalized)
**Projects** → **Elements** → **ElementResults** (normalized, per-pier data)

**Global Results** (Story-level):
```python
StoryDrift/Acceleration/Force/Displacement:
  story_id: FK → stories.id
  load_case_id: FK → load_cases.id
  result_category_id: FK → result_categories.id
  direction: String('X', 'Y')
  <value>: Float (drift, acceleration, force, displacement)
  max_<value>: Float (max value for envelope)
  min_<value>: Float (min value for envelope)
  story_sort_order: Integer  # Sheet-specific ordering (NEW in v1.4)
```

**Element Results** (Per-element, per-story):
```python
WallShear (Pier Forces):
  element_id: FK → elements.id
  story_id: FK → stories.id
  load_case_id: FK → load_cases.id
  direction: String('V2', 'V3')
  force: Float
  max_force, min_force: Float
  story_sort_order: Integer  # Per-element sheet ordering (NEW in v1.4)

QuadRotation (Quad Strain Gauges):
  element_id: FK → elements.id
  story_id: FK → stories.id
  load_case_id: FK → load_cases.id
  rotation: Float (radians)
  max_rotation, min_rotation: Float
  quad_name: String (optional)
  story_sort_order: Integer  # Per-element sheet ordering (NEW in v1.4)
```

**GlobalResultsCache** (Performance-optimized):
```python
project_id: FK → projects.id
result_set_id: FK → result_sets.id
result_type: String('Drifts', 'Accelerations', 'Forces', 'Displacements')
story_id: FK → stories.id
results_matrix: JSON  # {"TH01_X": 0.0123, "TH02_X": 0.0145, ...}
story_sort_order: Integer  # Preserves Excel sheet order (NEW in v1.4)
```

**ElementResultsCache** (Element performance-optimized):
```python
project_id: FK → projects.id
result_set_id: FK → result_sets.id
result_type: String('WallShears_V2', 'WallShears_V3', 'QuadRotations')
element_id: FK → elements.id
story_id: FK → stories.id
results_matrix: JSON  # {"TH01": 123.4, "TH02": 145.6, ...}
story_sort_order: Integer  # Per-element sheet order (NEW in v1.4)
```

### Sheet-Specific Story Ordering (NEW in v1.4)

**Problem Solved**: Different Excel sheets may have stories in different orders. For example:
- Story Drifts sheet: S4, S3, S2, S1, Base (top to bottom)
- Pier Forces sheet: S4, S2, Base (some piers don't span all stories)
- Quad Strain sheet: Sorted by pier/element name (P1, P10, P2, P3...), NOT by story

**Solution**: Each result record stores its `story_sort_order` from the source Excel sheet:
- `story_sort_order = 0` for first row in Excel, `1` for second row, etc.
- Display queries use `story_sort_order` from result/cache tables
- Preserves exact Excel sheet order for each result type
- Element results can have different story ordering per element

**Quad Rotations Exception**:
Quad rotation Excel sheets are sorted lexicographically by pier/element name, NOT by story height. Therefore:
- **Individual quad rotations**: Use global `Story.sort_order` (from Story Drifts sheet)
- **Max/Min quad rotations**: Use global `Story.sort_order`
- **All Rotations scatter plot**: Use global `Story.sort_order`
- Detection: Check if result type contains "QuadRotation" in service layer
- Re-sorting: `_order_element_cache_entries()` re-sorts by global `Story.sort_order` when quad rotation detected

**Implementation**:
- `ResultImportHelper._story_order` tracks Excel row indices during import
- All result models have `story_sort_order: Integer` column
- All cache models have `story_sort_order: Integer` column
- Repository queries order by `cache.story_sort_order.asc()` to preserve sheet order
- Service layer detects quad rotations and uses global ordering instead
- Key methods:
  - `get_element_maxmin_dataset()` - Lines 320-325: Quad rotation detection
  - `_order_element_cache_entries()` - Lines 469-500: Re-sorting logic
  - `get_all_quad_rotations_dataset()` - Line 851: Global sort order usage

### Indexing Strategy
- Composite indexes on `(project_id, name)` for uniqueness
- Composite indexes on `(story_id, load_case_id, direction)` for result queries
- Cache indexes on `(project_id, result_set_id, result_type)`
- Element cache indexes on `(element_id, story_id, result_type)`
- Element indexes on `(element_id, story_id, load_case_id)` for fast queries

---

## 5. Configuration System

### Result Type Configuration

**File**: `src/config/result_config.py`

```python
@dataclass
class ResultTypeConfig:
    name: str
    direction_suffix: str  # Column filter: '_X', '_UX', '_VX'
    unit: str              # Display unit: '%', 'g', 'kN'
    decimal_places: int
    multiplier: float      # Unit conversion
    y_label: str           # Plot axis label
    plot_mode: str         # 'building_profile', future: 'time_series'
    color_scheme: str      # 'blue_orange', 'green_red', etc.
```

**Registry Pattern**:
```python
RESULT_CONFIGS = {
    'Drifts': ResultTypeConfig(
        name='Drifts',
        direction_suffix='_X',
        unit='%',
        multiplier=100.0,
        decimal_places=2,
        y_label='Drift (%)',
        plot_mode='building_profile',
        color_scheme='blue_orange'
    ),
    'WallShears_V2': ResultTypeConfig(
        name='WallShears_V2',
        direction_suffix='',  # No column filtering (data already filtered)
        unit='kN',
        multiplier=1.0,
        decimal_places=0,
        y_label='V2 Shear (kN)',
        plot_mode='building_profile',
        color_scheme='blue_orange'
    ),
    'QuadRotations': ResultTypeConfig(
        name='QuadRotations',
        direction_suffix='',  # Directionless result (no X/Y split)
        unit='%',
        multiplier=1.0,  # Already converted in cache (radians → %)
        decimal_places=2,
        y_label='Rotation (%)',
        plot_mode='building_profile',
        color_scheme='blue_orange'
    ),
    # ... more configs
}

def get_config(result_type: str) -> ResultTypeConfig:
    return RESULT_CONFIGS.get(result_type, RESULT_CONFIGS['Drifts'])
```

**Directionless Results** (NEW in v1.4):
- QuadRotations has no X/Y or V2/V3 split
- `direction_suffix = ''` indicates directionless data
- Max/Min widget detects `directions = ("")` and shows single plot
- Column names: `Max_{LoadCase}`, `Min_{LoadCase}` (no direction suffix)
- UI hides Y direction completely (no empty space)

**All Rotations Visualization** (NEW in v1.4):
- Special scatter plot showing all quad rotation data points across all elements
- Treats stories as bins rather than exact values
- Applies vertical jitter (±0.3 range) to show distribution within each story
- Centered at x=0 to visualize positive/negative skewness
- Single orange color (#f97316) for all markers
- No legend (all data shown uniformly)
- Widget: `gui/all_rotations_widget.py`
- Data method: `result_service.get_all_quad_rotations_dataset()`

---

## 6. Transformer System

### Pluggable Data Transformation

**File**: `src/processing/result_transformers.py`

**Base Class**:
```python
class ResultTransformer(ABC):
    def __init__(self, result_type: str):
        self.config = get_config(result_type)

    @abstractmethod
    def filter_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        """Filter relevant columns (direction-specific)."""
        pass

    def clean_column_names(self, df: pd.DataFrame) -> pd.DataFrame:
        """Extract load case names from full column names."""
        # "160Wil_DES_Global_TH01_X" → "TH01"

    def add_statistics(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calculate Avg, Max, Min across load cases."""

    def transform(self, df: pd.DataFrame) -> pd.DataFrame:
        """Full pipeline: filter → clean → statistics."""
        df = self.filter_columns(df)
        df = self.clean_column_names(df)
        df = self.add_statistics(df)
        return df
```

**Concrete Implementation**:
```python
class DriftTransformer(ResultTransformer):
    def __init__(self):
        super().__init__('Drifts')

    def filter_columns(self, df):
        cols = [col for col in df.columns
                if col.endswith(self.config.direction_suffix)]
        return df[cols].copy()

# Register
TRANSFORMERS = {
    'Drifts': DriftTransformer(),
    'Accelerations': AccelerationTransformer(),
    'Forces': ForceTransformer(),
}
```

---

## 7. Utility Systems

### Color Utilities
```python
# src/utils/color_utils.py
COLOR_SCHEMES = {
    'blue_orange': ('#3b82f6', '#fb923c'),
    'green_red': ('#2ed573', '#e74c3c'),
    'cool_warm': ('#60a5fa', '#f87171'),
    'teal_yellow': ('#14b8a6', '#fbbf24'),
}

def get_gradient_color(value, min_val, max_val, scheme='blue_orange') -> QColor:
    """Get interpolated color for value using named scheme."""
```

### Plot Builder
```python
# src/utils/plot_builder.py
class PlotBuilder:
    def __init__(self, plot_widget, config):
        self.plot = plot_widget
        self.config = config

    def setup_axes(self, stories: list[str]):
        """Configure axes with story labels."""

    def set_story_range(self, num_stories, padding=0.02):
        """Set y-axis range with 2% padding."""

    def set_value_range(self, min_val, max_val,
                       left_padding=0.03, right_padding=0.05):
        """Set x-axis range with asymmetric padding."""

    def add_line(self, x_values, y_values, color, width=2):
        """Add a line to the plot."""

    def set_dynamic_tick_spacing(self, axis, min_val, max_val, num_intervals=6):
        """1-2-5 pattern, capped at 0.5 for drifts."""
```

---

## 8. UI Architecture

### Window Hierarchy
```
QApplication
├─> MainWindow
│   ├─> Header (64px fixed)
│   ├─> Project Cards Grid
│   └─> Action Buttons
│
└─> ProjectDetailWindow
    ├─> Header (64px fixed)
    ├─> 3-Panel Splitter
    │   ├─> Results Tree Browser (200px)
    │   ├─> Results Table (auto-fit)
    │   └─> Results Plot (remaining)
    │       ├─> Standard Plot (building profiles)
    │       ├─> Max/Min Plot (separate X/Y or single)
    │       └─> All Rotations Plot (scatter with jitter)
    └─> Status Bar
```

### Specialized Widgets

**All Rotations Widget** (`gui/all_rotations_widget.py`):
- Scatter plot for visualizing distribution of quad rotations
- Features:
  - Story bins with vertical jitter (±0.3) for visibility
  - Centered at x=0 with symmetric axis range
  - Small markers (size=4) in single orange color
  - No legend (uniform visualization)
  - Combines Max and Min data in single view
- Data source: `result_service.get_all_quad_rotations_dataset()`
- Ordering: Uses global `Story.sort_order` (not sheet-specific)

### Interactive Features

**Manual Selection System** (No Qt default styling):

```python
# Disable Qt selection to preserve gradient colors
table.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
table.setFocusPolicy(Qt.FocusPolicy.NoFocus)

# Manual state tracking
table._hovered_row = -1
table._selected_rows = set()

# Event handling
table.viewport().installEventFilter(self)  # Hover
table.cellClicked.connect(self._on_cell_clicked)  # Click
```

**Color Preservation**:
```python
# Store original color as COPY (not reference)
gradient_color = get_gradient_color(value, min_val, max_val, 'blue_orange')
item.setForeground(gradient_color)
item._original_color = QColor(gradient_color)  # Copy prevents mutation

# Restore on state change
def _apply_row_style(self, table, row):
    is_hovered = (row == table._hovered_row)
    is_selected = row in table._selected_rows

    for col in range(table.columnCount()):
        item = table.item(row, col)
        if item and hasattr(item, '_original_color'):
            # Always restore original foreground
            item.setForeground(item._original_color)
            # Apply background overlay only
            if is_hovered or is_selected:
                item.setBackground(QColor(103, 232, 249, 20))  # 8% cyan
            else:
                item.setBackground(QBrush())
```

**Why This Approach**:
- Qt's default selection changes both background AND foreground colors
- Storing QColor references causes mutation
- Storing QColor copies preserves original gradient values
- Background overlays provide visual feedback without affecting text color

### Component Communication

**Signal/Slot Architecture**:
```python
# Results Tree Browser → Project Detail Window
self.results_browser.selection_changed.connect(self.load_results)

# Table Widget → Plot Widget (column selection)
self.table_widget.selection_changed.connect(self.plot_widget.highlight_lines)

# Table Widget → Plot Widget (hover effects)
self.table_widget.load_case_hovered.connect(self.plot_widget.preview_line)
self.table_widget.hover_cleared.connect(self.plot_widget.clear_preview)
```

---

## 9. Data Flow

### Import Pipeline (Folder Batch)
```
1. User browses folder
   ↓
2. Discover all .xlsx/.xls files
   ↓
3. For each file:
   → Parse Excel (pandas)
   → Prefix load cases with filename
   → Transform data (ResultTransformer)
   → Bulk insert to database
   → Update progress
   ↓
4. Generate wide-format cache
   ↓
5. Refresh UI
```

### Display Pipeline

**Standard Results (Drifts, Accelerations, etc.)**:
```
1. User selects "Drifts" in tree browser
   ↓
2. Query GlobalResultsCache (wide-format JSON)
   ↓
3. Transform data:
   → get_transformer("Drifts")
   → filter columns, clean names, add statistics
   ↓
4. Display:
   → Table: Format using config (multiplier, unit, decimals)
   → Table: Apply gradient colors
   → Plot: Build using PlotBuilder
   → Plot: Render building profile
```

**All Rotations Scatter Plot**:
```
1. User selects "All Rotations" in tree browser
   ↓
2. Query QuadRotation table (all elements)
   → Join with LoadCase, Story, Element
   → Filter by project_id only (no element filter)
   ↓
3. Build dataset with global story ordering:
   → Convert radians to percentage (* 100)
   → Use Story.sort_order (not sheet-specific)
   → Sort by story order (bottom to top)
   ↓
4. Display scatter plot:
   → Apply vertical jitter (±0.3) per story bin
   → Center at x=0 with symmetric range
   → Single orange color, size=4 markers
   → No legend
```

---

## 10. Extension Points

### Adding New Result Type (10-15 lines)

```python
# 1. Configuration (result_config.py)
RESULT_CONFIGS['NewType'] = ResultTypeConfig(
    name='NewType',
    direction_suffix='_NX',
    unit='unit',
    decimal_places=2,
    multiplier=1.0,
    y_label='New Result',
    plot_mode='building_profile',
    color_scheme='blue_orange',
)

# 2. Transformer (result_transformers.py)
class NewTypeTransformer(ResultTransformer):
    def __init__(self):
        super().__init__('NewType')

    def filter_columns(self, df):
        return df[[col for col in df.columns
                   if col.endswith(self.config.direction_suffix)]].copy()

# 3. Register
TRANSFORMERS['NewType'] = NewTypeTransformer()

# Done! All UI components automatically support it.
```

### Adding New Color Scheme

```python
# color_utils.py
COLOR_SCHEMES['custom'] = ('#start_hex', '#end_hex')

# result_config.py
RESULT_CONFIGS['ResultType'].color_scheme = 'custom'
```

---

## 11. Performance Optimization

### Database
- **Bulk inserts**: 100+ rows/transaction using `bulk_insert_mappings()`
- **Indexed queries**: Composite indexes for fast lookups
- **Wide-format cache**: No JOINs needed for display (~20ms vs ~100ms)

### UI
- **PyQtGraph**: GPU-accelerated rendering, 100k+ data points
- **Fixed column widths**: No dynamic resizing overhead
- **Pre-calculated gradients**: Color utilities cache results
- **Hot-reload**: Auto-restart on file changes (~3s)

### Memory
- **Session management**: Proper cleanup with context managers
- **DataFrame operations**: Always use `.copy()` to avoid warnings

---

## 12. Development Patterns

### Adding Database Columns

```bash
# 1. Edit models.py
class Project(Base):
    new_field = Column(String(100))  # Add this

# 2. Generate migration
$ pipenv run alembic revision --autogenerate -m "Add new_field"

# 3. Review migration file in alembic/versions/

# 4. Apply migration
$ pipenv run alembic upgrade head
```

### Hot-Reload Development

```bash
$ pipenv run python dev_watch.py
# Edit any .py file in src/ → app restarts automatically
```

### Project Catalog Utilities
- Run `pipenv run python scripts/project_tools.py list` to see every project stored in the catalog with counts of load cases/stories/result sets.
- Run `pipenv run python scripts/project_tools.py delete --name <Project>` to remove the catalog entry **and** its per-project SQLite file (interactive confirmation unless `--force`).



---

## Appendix: Key Decisions

| Decision | Rationale | Trade-offs |
|----------|-----------|------------|
| **Hybrid data model** | Fast display + data integrity | Slightly more complex schema |
| **Configuration-driven** | Easy to add result types | Requires learning config system |
| **PyQtGraph not Matplotlib** | 100x faster for large datasets | Fewer plot types |
| **SQLite not PostgreSQL** | Local-first, no server setup | Single-user only |
| **Desktop-only (PyQt6)** | Full platform capabilities | No web/mobile |
| **Wide-format JSON cache** | Fast display without JOINs | Cache invalidation complexity |
| **Manual selection system** | Preserves gradient colors | More code than Qt defaults |
| **Per-result story ordering** | Preserves Excel sheet order exactly | story_sort_order in every result table |
| **Dual cache system** | Global + element results separation | More cache tables to maintain |
| **Quad rotation global ordering** | Correct story order despite lexicographic sheet sorting | Special case handling in service layer |

---

**Document Revision History**

| Version | Date | Changes |
|---------|------|---------|
| 1.4.1 | 2025-10-27 | All Rotations scatter plot, quad rotation global ordering exception, cache entry tuple fix |
| 1.4 | 2025-10-27 | Element results (WallShears, QuadRotations), sheet-specific story ordering (story_sort_order), directionless results support, ElementResultsCache |
| 1.3 | 2025-10-25 | Catalog/per-project DB split, ResultImportHelper, shared visual config/legend components, project_tools CLI |
| 1.2 | 2025-10-24 | Condensed to ~600 lines, removed redundancy |
| 1.1 | 2025-10-24 | Added interactive features, plot configuration |
| 1.0 | 2025-10-23 | Initial consolidated architecture doc |

---

**Related Documents**
- `PRD.md` - Product requirements and features
- `CLAUDE.md` - Development guide and code examples
- `README.md` - Project overview and setup
