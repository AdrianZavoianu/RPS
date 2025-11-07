# Architecture Documentation
## Results Processing System (RPS)

**Version**: 1.9
**Last Updated**: 2024-11-07
**Status**: Production-ready with element type separation, per-sheet conflict resolution, and optimized project structure

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
│   ├── result_config.py          # Result type configurations (dataclasses)
│   └── visual_config.py          # Visual styling constants, legend config
├── database/
│   ├── base.py                   # Per-project DB helpers / engine factory
│   ├── catalog_base.py           # Catalog engine + Base metadata
│   ├── catalog_models.py         # Catalog ORM definitions
│   ├── catalog_repository.py     # Catalog CRUD helpers
│   ├── models.py                 # Project-scoped ORM models (hybrid schema)
│   └── repository.py             # Project-scoped repositories
├── gui/
│   ├── styles.py                 # GMP design system colors and constants
│   ├── ui_helpers.py             # Styled component factory functions
│   ├── window_utils.py           # Platform-specific window utilities
│   ├── main_window.py            # Project cards view + navigation
│   ├── project_detail_window.py  # View orchestrator (shows/hides specialized widgets)
│   ├── results_tree_browser.py   # Hierarchical result navigation
│   ├── result_views/
│   │   └── standard_view.py      # Reusable table+plot view component
│   ├── results_table_widget.py   # Table with manual selection
│   ├── results_plot_widget.py    # PyQtGraph building profiles
│   ├── maxmin_drifts_widget.py   # Max/Min envelope visualization
│   ├── all_rotations_widget.py   # Scatter plot for all rotations
│   ├── beam_rotations_widget.py  # Beam rotation visualization
│   ├── folder_import_dialog.py   # Folder import with integrated load case selection (3-column layout)
│   ├── load_case_selection_dialog.py   # DEPRECATED: Minimalist load case list (replaced by inline selection)
│   ├── load_case_conflict_dialog.py    # Conflict resolution dialog (shown when duplicates exist)
│   └── components/
│       └── legend.py             # Reusable legend components
├── processing/
│   ├── excel_parser.py           # Excel file reading
│   ├── result_transformers.py    # Pluggable transformers
│   ├── import_context.py         # ResultImportHelper (shared import utilities)
│   ├── maxmin_calculator.py      # Absolute Max/Min calculations
│   ├── data_importer.py          # Single file → DB pipeline (per project)
│   ├── folder_importer.py        # Standard batch folder → DB pipeline (context-aware)
│   ├── enhanced_folder_importer.py  # Enhanced import with load case selection
│   ├── selective_data_importer.py   # Filtered import (only selected load cases)
│   ├── result_processor.py       # Result processing logic
│   └── result_service/           # Data retrieval service (modular package)
│       ├── __init__.py           # Public API exports
│       ├── service.py            # ResultDataService facade
│       ├── models.py             # Data models (ResultDataset, MaxMinDataset)
│       ├── cache_builder.py     # Standard/element dataset builders
│       ├── maxmin_builder.py    # Max/min dataset builders
│       ├── metadata.py          # Display label utilities
│       └── story_loader.py      # StoryProvider caching helper
├── services/
│   └── project_service.py        # Catalog + project context management
└── utils/
    ├── slug.py                   # Slug utilities for project folders
    ├── color_utils.py            # Gradient color interpolation
    ├── data_utils.py             # Parsing/formatting helpers
    ├── plot_builder.py           # Declarative plot construction
    └── env.py                    # Environment detection utilities
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

### Complete Data Model

The application uses two separate databases:
- **Catalog DB** (`data/catalog.db`) - Project metadata
- **Per-Project DBs** (`data/projects/<slug>/<slug>.db`) - Project-specific data

**Quick Navigation**:
- [Catalog Database](#catalog-database-datacatalogdb) - 1 table (CatalogProject)
- [Foundation Tables](#1-foundation-tables) - 6 tables (Project, Story, LoadCase, ResultSet, ResultCategory, Element)
- [Global Result Tables](#2-global-result-tables-story-level) - 4 tables (StoryDrift, StoryAcceleration, StoryForce, StoryDisplacement)
- [Element Result Tables](#3-element-result-tables-element-level) - 6 tables (WallShear, QuadRotation, ColumnShear, ColumnAxial, ColumnRotation, BeamRotation)
- [Cache Tables](#4-cache-tables-performance-optimization) - 3 tables (GlobalResultsCache, ElementResultsCache, AbsoluteMaxMinDrift)
- [Future Tables](#5-futureholder-tables) - 1 table (TimeHistoryData - placeholder)

**Total Tables**: 21 (1 catalog + 20 per-project)

---

#### Catalog Database (`data/catalog.db`)

**CatalogProject** - Project registry
```python
id: Integer (PK, auto-increment)
name: String(255) unique, not null           # Display name
slug: String(255) unique, not null           # URL-safe identifier
description: Text, nullable                  # Project description
db_path: String(512), not null               # Path to project database
created_at: DateTime, default=now()
updated_at: DateTime, auto-update
last_opened: DateTime, nullable

Purpose: Central registry of all projects, maps names to database files
```

---

#### Per-Project Database Schema

##### 1. Foundation Tables

**Project** - Project metadata (one per database)
```python
id: Integer (PK)
name: String(255) unique, not null
description: Text, nullable
created_at: DateTime
updated_at: DateTime

Relationships:
  → load_cases (cascade delete)
  → stories (cascade delete)
  → result_sets (cascade delete)

Purpose: Root entity for project-scoped data
```

**Story** - Building floors/levels
```python
id: Integer (PK)
project_id: Integer FK → projects.id, not null
name: String(100), not null                  # "Base", "S1", "S2", etc.
elevation: Float, nullable                   # Elevation in project units
sort_order: Integer, nullable                # Global ordering (bottom=0)

Indexes:
  - UNIQUE(project_id, name)

Relationships:
  → drifts, accelerations, forces, displacements (cascade delete)

Purpose: Represents building stories, maintains global vertical ordering
```

**LoadCase** - Analysis load cases
```python
id: Integer (PK)
project_id: Integer FK → projects.id, not null
name: String(100), not null                  # "TH01", "MCR1", etc.
case_type: String(50), nullable              # "Time History", "Modal", etc.
description: Text, nullable

Indexes:
  - UNIQUE(project_id, name)

Relationships:
  → story_drifts, story_accelerations, story_forces, story_displacements
  → wall_shears, column_shears, column_rotations

Purpose: Shared load case registry across all result types
```

**ResultSet** - Result collections (DES, MCE, SLE, etc.)
```python
id: Integer (PK)
project_id: Integer FK → projects.id, not null
name: String(100), not null                  # "DES", "MCE", "SLE"
description: Text, nullable
created_at: DateTime

Indexes:
  - UNIQUE(project_id, name)

Relationships:
  → categories (cascade delete)
  → cache_entries (cascade delete)

Purpose: Organizes results into named sets for comparison
```

**ResultCategory** - Result hierarchy (Envelopes/Time-Series → Global/Elements)
```python
id: Integer (PK)
result_set_id: Integer FK → result_sets.id, not null
category_name: String(50), not null          # "Envelopes", "Time-Series"
category_type: String(50), not null          # "Global", "Elements", "Joints"

Indexes:
  - UNIQUE(result_set_id, category_name, category_type)

Relationships:
  → drifts, accelerations, forces, displacements, wall_shears, etc.

Purpose: Two-level categorization within result sets
```

**Element** - Structural elements (walls, columns, beams, quads)
```python
id: Integer (PK)
project_id: Integer FK → projects.id, not null
element_type: String(50), not null           # "Wall", "Quad", "Column", "Beam"
name: String(100), not null                  # Display name
unique_name: String(100), nullable           # ETABS/SAP2000 identifier
story_id: Integer FK → stories.id, nullable

Indexes:
  - UNIQUE(project_id, element_type, unique_name)

Relationships:
  → wall_shears, quad_rotations, column_shears, column_axials, column_rotations, beam_rotations

Purpose: Registry of structural elements for element-level results

**Important**: Element types are strictly separated:
- "Wall" - Pier forces/shears (e.g., P1, P2, WALL1)
- "Quad" - Quad rotations (e.g., Quad A-2, Quad B-1) - separate from walls!
- "Column" - Column forces/rotations (e.g., C1, C2, COL123)
- "Beam" - Beam rotations (e.g., B1, B2, BEAM456)
```

---

##### 2. Global Result Tables (Story-Level)

**StoryDrift** - Story drift ratios
```python
id: Integer (PK)
story_id: Integer FK → stories.id, not null
load_case_id: Integer FK → load_cases.id, not null
result_category_id: Integer FK → result_categories.id, nullable
direction: String(10), not null              # "X" or "Y"
drift: Float, not null                       # Drift ratio
max_drift: Float, nullable                   # Envelope max
min_drift: Float, nullable                   # Envelope min
story_sort_order: Integer, nullable          # Sheet-specific ordering

Indexes:
  - (story_id, load_case_id, direction)
  - (result_category_id)

Source Sheet: "Story Drifts"
```

**StoryAcceleration** - Story accelerations
```python
id: Integer (PK)
story_id: Integer FK → stories.id, not null
load_case_id: Integer FK → load_cases.id, not null
result_category_id: Integer FK → result_categories.id, nullable
direction: String(10), not null              # "UX" or "UY"
acceleration: Float, not null                # Acceleration in g
max_acceleration: Float, nullable
min_acceleration: Float, nullable
story_sort_order: Integer, nullable

Indexes:
  - (story_id, load_case_id, direction)
  - (result_category_id)

Source Sheet: "Diaphragm Accelerations"
```

**StoryForce** - Story shear forces
```python
id: Integer (PK)
story_id: Integer FK → stories.id, not null
load_case_id: Integer FK → load_cases.id, not null
result_category_id: Integer FK → result_categories.id, nullable
direction: String(10), not null              # "VX" or "VY"
location: String(20), nullable               # "Top" or "Bottom"
force: Float, not null                       # Shear force
max_force: Float, nullable
min_force: Float, nullable
story_sort_order: Integer, nullable

Indexes:
  - (story_id, load_case_id, direction)
  - (result_category_id)

Source Sheet: "Story Forces"
```

**StoryDisplacement** - Story displacements
```python
id: Integer (PK)
story_id: Integer FK → stories.id, not null
load_case_id: Integer FK → load_cases.id, not null
result_category_id: Integer FK → result_categories.id, nullable
direction: String(10), not null              # "UX", "UY", "UZ"
displacement: Float, not null
max_displacement: Float, nullable
min_displacement: Float, nullable
story_sort_order: Integer, nullable

Indexes:
  - (story_id, load_case_id, direction)
  - (result_category_id)

Source Sheet: "Joint Displacements"
```

---

##### 3. Element Result Tables (Element-Level)

**WallShear** - Wall/pier shear forces
```python
id: Integer (PK)
element_id: Integer FK → elements.id, not null
story_id: Integer FK → stories.id, not null
load_case_id: Integer FK → load_cases.id, not null
result_category_id: Integer FK → result_categories.id, nullable
direction: String(10), not null              # "V2" or "V3"
location: String(20), nullable               # "Bottom" (only used for shears)
force: Float, not null
max_force: Float, nullable
min_force: Float, nullable
story_sort_order: Integer, nullable          # Per-element sheet ordering

Indexes:
  - (element_id, story_id, load_case_id, direction)
  - (result_category_id)

Source Sheet: "Pier Forces"
```

**QuadRotation** - Quad strain gauge rotations
```python
id: Integer (PK)
element_id: Integer FK → elements.id, not null
story_id: Integer FK → stories.id, not null
load_case_id: Integer FK → load_cases.id, not null
result_category_id: Integer FK → result_categories.id, nullable
quad_name: String(50), nullable              # Quad element identifier
direction: String(20), nullable              # "Pier" (typically)
rotation: Float, not null                    # Rotation in radians
max_rotation: Float, nullable                # Radians
min_rotation: Float, nullable                # Radians
story_sort_order: Integer, nullable

Indexes:
  - (element_id, story_id, load_case_id)
  - (result_category_id)

Source Sheet: "Quad Strain Gauge - Rotation"
Display: Multiplied by 100 to show as percentage
Note: Uses global Story.sort_order (not sheet-specific ordering)
```

**ColumnShear** - Column shear forces
```python
id: Integer (PK)
element_id: Integer FK → elements.id, not null
story_id: Integer FK → stories.id, not null
load_case_id: Integer FK → load_cases.id, not null
result_category_id: Integer FK → result_categories.id, nullable
direction: String(10), not null              # "V2" or "V3"
location: String(20), nullable               # "Top" or "Bottom"
force: Float, not null
max_force: Float, nullable
min_force: Float, nullable
story_sort_order: Integer, nullable

Indexes:
  - (element_id, story_id, load_case_id, direction)
  - (result_category_id)

Source Sheet: "Element Forces - Columns"
```

**ColumnAxial** - Column minimum axial forces
```python
id: Integer (PK)
element_id: Integer FK → elements.id, not null
story_id: Integer FK → stories.id, not null
load_case_id: Integer FK → load_cases.id, not null
result_category_id: Integer FK → result_categories.id, nullable
location: String(20), nullable               # "Top" or "Bottom"
min_axial: Float, not null                   # Most compression P value
story_sort_order: Integer, nullable

Indexes:
  - (element_id, story_id, load_case_id)
  - (result_category_id)

Source Sheet: "Element Forces - Columns"
Purpose: Captures minimum (most compression) axial forces
```

**ColumnRotation** - Column plastic hinge rotations
```python
id: Integer (PK)
element_id: Integer FK → elements.id, not null
story_id: Integer FK → stories.id, not null
load_case_id: Integer FK → load_cases.id, not null
result_category_id: Integer FK → result_categories.id, nullable
direction: String(10), not null              # "R2" or "R3"
rotation: Float, not null                    # Rotation in radians
max_rotation: Float, nullable
min_rotation: Float, nullable
story_sort_order: Integer, nullable

Indexes:
  - (element_id, story_id, load_case_id, direction)
  - (result_category_id)

Source Sheet: "Fiber Hinge States"
Filter: Frame/Wall starts with 'C'
Display: Multiplied by 100 to show as percentage
```

**BeamRotation** - Beam plastic hinge rotations
```python
id: Integer (PK)
element_id: Integer FK → elements.id, not null
story_id: Integer FK → stories.id, not null
load_case_id: Integer FK → load_cases.id, not null
result_category_id: Integer FK → result_categories.id, nullable
hinge: String(20), nullable                  # Hinge identifier (e.g., "SB2")
generated_hinge: String(20), nullable        # Generated ID (e.g., "B19H1")
rel_dist: Float, nullable                    # Relative distance along beam
r3_plastic: Float, not null                  # R3 plastic rotation in radians
max_r3_plastic: Float, nullable
min_r3_plastic: Float, nullable
story_sort_order: Integer, nullable

Indexes:
  - (element_id, story_id, load_case_id)
  - (result_category_id)

Source Sheet: "Hinge States"
Filter: Frame/Wall starts with 'B'
Display: Multiplied by 100 to show as percentage
```

---

##### 4. Cache Tables (Performance Optimization)

**GlobalResultsCache** - Wide-format global results
```python
id: Integer (PK)
project_id: Integer FK → projects.id, not null
result_set_id: Integer FK → result_sets.id, nullable
result_type: String(50), not null            # "Drifts", "Accelerations", etc.
story_id: Integer FK → stories.id, not null
results_matrix: JSON, not null               # {"TH01_X": 0.0123, "TH02_X": 0.0145, ...}
story_sort_order: Integer, nullable          # Preserves Excel sheet order
last_updated: DateTime, auto-update

Indexes:
  - (project_id, result_set_id, result_type)
  - (story_id)

Purpose: One row per story, all load cases in JSON for fast table display
Format: Load case + direction as key, value as float
Performance: ~20ms vs ~100ms for JOIN queries
```

**ElementResultsCache** - Wide-format element results
```python
id: Integer (PK)
project_id: Integer FK → projects.id, not null
result_set_id: Integer FK → result_sets.id, nullable
result_type: String(50), not null            # "WallShears_V2", "QuadRotations", etc.
element_id: Integer FK → elements.id, not null
story_id: Integer FK → stories.id, not null
results_matrix: JSON, not null               # {"TH01": 123.4, "TH02": 145.6, ...}
story_sort_order: Integer, nullable          # Per-element sheet ordering
last_updated: DateTime, auto-update

Indexes:
  - (project_id, result_set_id, result_type, element_id)
  - (element_id)
  - (story_id)

Purpose: One row per (element, story), all load cases in JSON
Format: Load case as key (direction in result_type), value as float
```

**AbsoluteMaxMinDrift** - Computed envelope results
```python
id: Integer (PK)
project_id: Integer FK → projects.id, not null
result_set_id: Integer FK → result_sets.id, not null
story_id: Integer FK → stories.id, not null
load_case_id: Integer FK → load_cases.id, not null
direction: String(10), not null              # "X" or "Y"
absolute_max_drift: Float, not null          # max(|Max|, |Min|)
sign: String(10), not null                   # "positive" or "negative"
original_max: Float, not null                # Original Max value
original_min: Float, not null                # Original Min value
created_at: DateTime

Indexes:
  - UNIQUE(project_id, result_set_id, story_id, load_case_id, direction)
  - (result_set_id)

Purpose: Pre-computed absolute maximum drifts for envelope visualization
Calculation: Compares |Max| vs |Min|, stores larger absolute value + sign
```

---

##### 5. Future/Placeholder Tables

**TimeHistoryData** - Time-series results (placeholder)
```python
id: Integer (PK)
load_case_id: Integer FK → load_cases.id, not null
element_id: Integer FK → elements.id, nullable
story_id: Integer FK → stories.id, nullable
result_type: String(50), not null            # "Drift", "Acceleration", etc.
time_step: Float, not null                   # Time in seconds
value: Float, not null
direction: String(10), nullable

Indexes:
  - (load_case_id, result_type)
  - (element_id)

Purpose: Future support for time-history plotting
Status: Table exists, not yet populated by importers
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

### Indexing Strategy Summary

All indexes are documented above in the Complete Data Model section. Key patterns:

**Uniqueness Constraints**:
- `(project_id, name)` - Projects, Stories, LoadCases, ResultSets
- `(project_id, element_type, unique_name)` - Elements
- `(result_set_id, category_name, category_type)` - ResultCategories

**Query Performance Indexes**:
- Global Results: `(story_id, load_case_id, direction)` + `(result_category_id)`
- Element Results: `(element_id, story_id, load_case_id, [direction])` + `(result_category_id)`
- Cache Lookups: `(project_id, result_set_id, result_type)` for global, add `element_id` for element cache
- Envelope Results: `(project_id, result_set_id, story_id, load_case_id, direction)` for AbsoluteMaxMinDrift

**Design Notes**:
- Composite indexes enable fast filtering by multiple criteria (story + load case + direction)
- Category indexes support hierarchical tree navigation
- Cache indexes optimize the most common query pattern (load all results for visualization)

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
│   ├─> Header (64px fixed) with navigation
│   ├─> Stacked Pages (Home | Projects | Docs)
│   │   └─> Projects Page: Project Cards Grid
│   └─> Status Bar
│
├─> FolderImportDialog (modal)
│   ├─> Header (24px title: "Import Project Data")
│   ├─> Top Row (3 sections with equal 12px padding)
│   │   ├─> Folder Selection (stretch=2, orange border)
│   │   ├─> Project (stretch=1, normal border)
│   │   └─> Result Set (stretch=1, orange border)
│   ├─> Bottom Row (async data loading)
│   │   ├─> Files to Process (stretch=3, file list)
│   │   ├─> Load Cases (stretch=2, checkboxes with ✓)
│   │   └─> Import Progress (stretch=5, log + progress bar)
│   └─> Action Buttons (Start Import, Cancel)
│
└─> ProjectDetailWindow (per project)
    ├─> Header (64px fixed) with actions
    ├─> 2-Panel Splitter
    │   ├─> Results Tree Browser (200px)
    │   └─> Content Area (dynamic view switching)
    │       ├─> StandardResultView (table + plot splitter)
    │       ├─> MaxMinDriftsWidget (separate X/Y or single plot)
    │       ├─> AllRotationsWidget (scatter with jitter)
    │       └─> BeamRotationsTable (wide-format table)
    └─> Status Bar
```

### Import Dialog Architecture (v1.9 - Nov 6, 2024)

**Modern Async Import UI** (`gui/folder_import_dialog.py`):

**Threading Model**:
- `LoadCaseScanWorker(QThread)` - Background load case scanning
- `FolderImportWorker(QThread)` - Background import processing
- `QApplication.processEvents()` - Immediate UI feedback on button clicks

**Layout Strategy**:
```
Top Row (stretch ratio 2:1:1):
┌──────────────────┐ ┌────────┐ ┌────────┐
│ Folder (2)       │ │Proj (1)│ │Res (1) │
│ 🟠/🔵 dynamic    │ │        │ │🟠/🔵   │
└──────────────────┘ └────────┘ └────────┘

Bottom Row (stretch ratio 49:30:81 for pixel-perfect alignment):
┌──────────────┐ ┌────────┐ ┌─────────────────────┐
│ Files  (49)  │ │Load(30)│ │  Progress  (81)     │
│ file1.xlsx   │ │☑ TH01  │ │ [=====>      ] 50%  │
│ file2.xlsx   │ │☑ TH02  │ │ Scanning files...   │
└──────────────┘ └────────┘ └─────────────────────┘
```

**Visual Design** (Nov 6, 2024 refinement):
- **Title**: "Import Project Data" at 24px font (prominent header)
- **Dynamic Borders**: Smart visual feedback on required fields
  - 🟠 Orange (#ff8c00): Empty required field
  - 🔵 Blue (accent): Field has focus (editing)
  - ⚪ Gray (border): Field filled (normal)
- **Full-Page Layout**: Minimal margins for maximum space
  - Top margin: 24px → 16px
  - Spacing: 16px → 12px
  - Groupbox padding: 12px → 8px
  - Input padding: 8px → 6px
- **Perfect Alignment**: Fine-tuned stretch ratios (49:30:81)
  - Files + LoadCases right edge aligns with Folder right edge
  - Progress left edge aligns with Project left edge

**Performance Optimizations**:
- **Folder Selection**: Background scan with `LoadCaseScanWorker`
  - Was: 20s UI freeze
  - Now: 0s freeze, real-time progress updates
- **Start Import**: Cached conflict detection
  - Was: 10s UI freeze (rescanning files)
  - Now: 0s freeze (reuses `self.load_case_sources` from initial scan)
- **Import Process**: Worker thread with progress signals
  - Real-time progress bar and log updates
  - UI remains fully responsive

**Checkbox Implementation**:
- Dynamic text labels with checkmark: `f"  ✓  {load_case}"`
- State change callback updates label text
- Cyan background (#4a7d89) when checked
- 20px indicators with 2px borders

**Signal Flow**:
```
User Action → UI Update → Worker Thread → Progress Signals → UI Feedback

1. Browse Folder:
   folder_input.setText() → processEvents() → LoadCaseScanWorker.start()
   → progress signal → update progress bar → finished signal → populate checkboxes

2. Start Import:
   progress_label.setText() → processEvents() → check conflicts (cached)
   → FolderImportWorker.start() → progress signals → real-time log updates

3. Checkbox Toggle:
   stateChanged signal → update_label() → setText("  ✓  ..." or "      ...")
```

**Key Files**:
- `gui/folder_import_dialog.py` - Main dialog (lines 151-930)
- `processing/enhanced_folder_importer.py` - Orchestration (lines 20-610)
- `processing/selective_data_importer.py` - Filtered import (extends DataImporter)
- `gui/load_case_conflict_dialog.py` - Conflict resolution UI (shown when needed)

### View Pattern: StandardResultView

**Reusable Component** (`gui/result_views/standard_view.py`):
- Encapsulates the common table+plot pattern
- Internal horizontal splitter with table (left) and plot (right)
- Handles signal connections between table and plot automatically
- Clean public API: `set_dataset(dataset)` and `clear()`

```python
class StandardResultView(QWidget):
    def __init__(self):
        self.table = ResultsTableWidget()
        self.plot = ResultsPlotWidget()
        # Configure splitter, connect signals

    def set_dataset(self, dataset: ResultDataset):
        self.table.load_dataset(dataset)
        self.plot.load_dataset(dataset)

    def clear(self):
        self.table.clear_data()
        self.plot.clear_plots()
```

**Benefits**:
- Single source of truth for table+plot layout
- Consistent signal wiring (selection, hover)
- Reduces duplication in `ProjectDetailWindow`
- Easy to maintain and extend

### View Orchestration: ProjectDetailWindow

**Dynamic View Switching**:
- Maintains multiple specialized widgets, shows/hides based on selection
- View selection logic in `on_browser_selection_changed()`

```python
# Show appropriate widget based on result type
if result_type == "AllQuadRotations":
    self.standard_view.hide()
    self.maxmin_widget.hide()
    self.all_rotations_widget.show()  # Show scatter plot
    self.beam_rotations_table.hide()
elif result_type.startswith("MaxMin"):
    self.standard_view.hide()
    self.maxmin_widget.show()  # Show envelope view
    self.all_rotations_widget.hide()
    self.beam_rotations_table.hide()
elif result_type == "BeamRotationsTable":
    self.standard_view.hide()
    self.beam_rotations_table.show()  # Show wide table
    # ... hide others
else:
    self.standard_view.show()  # Standard table+plot
    # ... hide others
```

**Specialized Widgets**:
1. **StandardResultView** - Directional results (Drifts X/Y, Forces, etc.)
2. **MaxMinDriftsWidget** - Envelope max/min with separate X/Y plots
3. **AllRotationsWidget** - Scatter plot for rotation distributions
4. **BeamRotationsTable** - Wide-format table for beam rotations

### Results Tree Browser & Data Detection

**Smart Data Detection System** (`gui/project_detail_window.py:252-289`):
- Queries cache tables on project load to determine which result types have data
- `_get_available_result_types()` method:
  - Queries `GlobalResultsCache.result_type` for global results (Drifts, Accelerations, Forces)
  - Queries `ElementResultsCache.result_type` for element results (WallShears, ColumnShears, etc.)
  - Extracts base type names from cache (e.g., "WallShears_V2" → "WallShears")
  - Returns dict mapping `result_set_id` to set of available result types
- Backward compatible: If no data detection info provided, shows all sections

**Conditional Section Rendering** (`gui/results_tree_browser.py`):
- `_has_data_for(result_set_id, result_type)` checks availability before rendering
- Sections automatically hidden if no data exists:
  - **Global results**: Drifts, Accelerations, Forces, Displacements (lines 186-219)
  - **Walls section**: Only shown if WallShears or QuadRotations data exists (lines 329-356)
  - **Columns section**: Only shown if ColumnShears, ColumnAxials, or ColumnRotations exist (lines 528-560)
  - **Beams section**: Only shown if BeamRotations data exists (lines 762-784)
- Reduces browser clutter when partial datasets are imported

**Default Expansion States** (v1.7):
- **Expanded sections** (show result type names at a glance):
  - Global section (`global_item.setExpanded(True)`) - shows Drifts, Forces, etc.
  - Elements section (`elements_item.setExpanded(True)`) - shows Walls, Columns, Beams
- **Collapsed sections** (hide details until clicked):
  - Result types (`drifts_parent.setExpanded(False)`) - hides X/Y directions, Max/Min
  - Element categories (`walls_parent.setExpanded(False)`) - hides Shears/Rotations subcategories
- **Rationale**: Balance between overview and detail - user sees what's available without visual clutter

**Layout Optimization** (v1.7):
- StandardResultView splitter: 60/40 table/plot split (better plot visibility)
- Table font: 10px (compact without horizontal scrolling)
- Legend: Below plots in 4-column grid (saves horizontal space)
- Max/Min tables: Ultra-compact (7px font, 0px 1px padding) for small screens
- Plot titles removed to maximize visualization area

### Specialized Widgets

**All Rotations Widget** (`gui/all_rotations_widget.py`):
- Scatter plot for visualizing distribution of quad/column/beam rotations
- Features:
  - Story bins with vertical jitter (±0.3) for visibility
  - Centered at x=0 with symmetric axis range
  - Small markers (size=4) in single orange color
  - No legend (uniform visualization)
  - Combines Max and Min data in single view
- Data source: `result_service.get_all_quad_rotations_dataset()` (and similar for columns/beams)
- Ordering: Uses global `Story.sort_order` (not sheet-specific)

**Window Utilities** (`gui/window_utils.py`):
- Platform-specific window enhancements
- `enable_dark_title_bar(window)` - Windows 10/11 dark title bar via DWM API
- `set_windows_app_id(app_id)` - Taskbar integration on Windows
- Gracefully handles non-Windows platforms (no-op)

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
self.browser.selection_changed.connect(self.on_browser_selection_changed)
# Signal signature: (result_set_id, category, result_type, direction, element_id)

# StandardResultView internal connections (automatic)
self.table.selection_changed.connect(self.plot.highlight_load_cases)
self.table.load_case_hovered.connect(self.plot.hover_load_case)
self.table.hover_cleared.connect(self.plot.clear_hover)
```

**View Switching Flow**:
```
1. User clicks tree item in ResultsTreeBrowser
   ↓
2. Browser emits selection_changed signal with parameters
   ↓
3. ProjectDetailWindow.on_browser_selection_changed() receives signal
   ↓
4. Determines which widget to show based on result_type
   ↓
5. Hides all widgets, shows selected widget
   ↓
6. Loads data into selected widget via ResultDataService
   ↓
7. Widget displays data (table+plot, envelope, scatter, etc.)
```

---

## 8.5. Integrated Load Case Selection Architecture

### Overview

The integrated load case selection provides a streamlined single-page workflow for selecting load cases and resolving conflicts when importing from multiple Excel files. This addresses the common scenario where load cases are split across files for computational efficiency, or when test/preliminary cases need to be filtered out.

**Key Components**:
1. **FolderImportDialog** - Main import dialog with three-column layout (Files | Load Cases | Progress)
2. **LoadCaseConflictDialog** - Conflict resolution dialog (only shown when duplicates exist)
3. **EnhancedFolderImporter** - Orchestrates the enhanced import workflow
4. **SelectiveDataImporter** - Filters dataframes before import

### Component Architecture

```
FolderImportDialog (GUI) - Single Page with 3 Columns
├─> Column 1: Files to Process (compact list)
├─> Column 2: Load Cases (inline checkbox selection)
│   ├─> Auto-scans when folder selected
│   ├─> Checkboxes for all discovered load cases
│   ├─> "All" / "None" quick action buttons
│   └─> Modern styling (20px checkboxes, cyan accent)
├─> Column 3: Import Progress (status + log)
└─> FolderImportWorker (background thread)
    ├─> if selected_load_cases exists and > 0:
    │   └─> EnhancedFolderImporter
    │       ├─> Conflict detection (in main thread before worker)
    │       ├─> LoadCaseConflictDialog (if conflicts, main thread, modal)
    │       └─> SelectiveDataImporter (per file)
    │           └─> Filter dataframe → DataImporter logic
    └─> else:
        └─> FolderImporter (standard import, all load cases)
```

### Workflow Details

**Phase 1: Auto-Scan on Folder Selection** (Main Thread)
```python
# FolderImportDialog._scan_load_cases() - triggered by browse_folder()
file_load_cases = EnhancedFolderImporter.prescan_folder_for_load_cases(...)
# Collect unique load cases and sources
all_load_cases = set()
load_case_sources = {}  # load_case → [(file, sheet), ...]
# Populate inline checkbox list
self._populate_load_case_list(sorted(all_load_cases))
# Result: UI shows checkboxes for all discovered load cases (all checked by default)
```

**Phase 2: User Selection** (Inline UI)
```python
# FolderImportDialog - Load Cases column
- Scrollable checkbox list (modern design: 20px boxes, 2px borders, cyan accent)
- "All" / "None" quick action buttons at top
- User clicks checkboxes to select/deselect
- No separate dialog - all inline in main import window
```

**Phase 3: Conflict Detection** (Main Thread, on Start Import click)
```python
# FolderImportDialog._handle_conflicts()
selected_load_cases = self._get_selected_load_cases()
# Build conflict structure: {load_case: {sheet: [file1, file2, ...]}}
for lc in selected_load_cases:
    sources = self.load_case_sources.get(lc, [])  # [(file, sheet), ...]
    if len(sources) > 1:
        # Group by sheet
        sheet_files = {}
        for file_name, sheet_name in sources:
            sheet_files[sheet_name].append(file_name)
        # Check for actual conflicts (same sheet in multiple files)
        if any(len(files) > 1 for files in sheet_files.values()):
            conflicts[lc] = sheet_files
```

**Phase 4: Conflict Resolution** (Only if conflicts exist)
```python
# LoadCaseConflictDialog (modal popup)
- For each conflict:
    - Radio buttons: Choose file1 | Choose file2 | Skip this case
    - Quick actions: Use first file for all | Use last file for all
- Returns: {load_case: chosen_file}
- Transform to format expected by worker: {sheet: {load_case: file}}
```

**Phase 5: Selective Import** (Background Worker Thread)
```python
# SelectiveDataImporter (extends DataImporter)
def _import_story_drifts(self, session, project_id):
    df, load_cases, stories = self.parser.get_story_drifts()

    # Filter load cases
    filtered_cases = [lc for lc in load_cases if lc in self.allowed_load_cases]
    if not filtered_cases:
        return stats  # Skip this result type

    # Filter dataframe (early filtering for performance)
    df = df[df['Output Case'].isin(filtered_cases)].copy()

    # Continue with normal DataImporter logic
    # (transforms, bulk insert, cache generation)
```

### Design Decisions

**Why Inheritance (SelectiveDataImporter extends DataImporter)?**
- Reuses all existing import logic (transformers, cache generation, error handling)
- Only overrides data filtering step
- Maintains consistency with standard import
- ~550 lines vs ~2000 lines if reimplemented

**Why Early Dataframe Filtering?**
```python
# Good: Filter first, process less data
df = df[df['Output Case'].isin(allowed)].copy()
processed = ResultProcessor.process_story_drifts(df, ...)

# Bad: Process all data, filter objects later
processed = ResultProcessor.process_story_drifts(df, ...)
filtered = [obj for obj in processed if obj.load_case in allowed]
```
Benefits: Less memory, faster processing, simpler logic

**Why Worker Thread for Enhanced Import?**
- Dialogs must run on main thread (Qt requirement)
- Import processing runs on background thread (non-blocking UI)
- Worker calls `dialog.exec()` which blocks worker thread but not main thread
- User sees responsive UI during file scanning and import

### Benefits of Integrated Approach

**UX Improvements**:
- ✅ Single-page experience - no popup dialogs for load case selection
- ✅ All context visible at once (files, load cases, progress)
- ✅ Faster workflow - fewer clicks and context switches
- ✅ Immediate visual feedback when selecting folder (load cases appear automatically)
- ✅ Modern, clean design with clear checkboxes (20px, 2px borders, cyan accent)

**Technical Improvements**:
- ✅ Load case scanning happens in main thread (no blocking)
- ✅ Conflict resolution only shows when actually needed
- ✅ Proper data transformation: `{load_case: file}` → `{sheet: {load_case: file}}`
- ✅ Backward compatible - standard import if no load cases selected

**Default Behavior**:
- All load cases checked by default (user can deselect unwanted ones)
- If no load cases selected: Standard import (all load cases imported)
- If some selected: Enhanced import with selective filtering
- Conflict dialog only appears when actual conflicts exist

### File Statistics

**Status**: ✅ Fully functional as of Nov 7, 2024 (integrated UI, element type separation, per-sheet conflict resolution)

**Key Files**:
- `gui/folder_import_dialog.py` - Redesigned with 3-column layout, inline load case selection (~800 lines total)
- `gui/load_case_selection_dialog.py` - DEPRECATED: Minimalist standalone dialog (replaced by inline selection)
- `gui/load_case_conflict_dialog.py` - Conflict resolution dialog (350 lines, only shown when needed)
- `processing/enhanced_folder_importer.py` - Enhanced import orchestration (550 lines)
- `processing/selective_data_importer.py` - Filtered import logic (700 lines, includes element import fixes)

**Total Code**: ~2400 lines for enhanced import system

**Bug Fixes Applied** (Nov 4-7, 2024):
- **Element Type Separation** (Nov 7): Fixed Quad vs Wall element type confusion in 4 locations (import, selective import, browser UI, cache generation). See `docs/fixes/QUAD_WALL_ELEMENT_TYPE_FIX.md`
- **Per-Sheet Conflict Resolution** (Nov 7): Changed conflict dialog to track `{sheet: {load_case: file}}` instead of `{load_case: file}`. Each result type can now have different file choices. See `docs/fixes/PER_SHEET_CONFLICT_RESOLUTION_FIX.md`
- Fixed column name mismatches (UX→Ux, OutputCase→"Output Case")
- Implemented element dictionary pattern for all element types
- Corrected field names (shear→force, axial→force, Rotation→R3Plastic)
- Replaced non-existent bulk_create methods with session.bulk_save_objects()

### Critical Implementation Notes (Nov 4-7, 2024)

**Bulk Insert Pattern**:
All element imports MUST use `session.bulk_save_objects()` directly, NOT repository methods:
```python
# ✅ CORRECT - Direct SQLAlchemy bulk insert
session.bulk_save_objects(element_objects)
session.commit()

# ❌ INCORRECT - ElementRepository doesn't have bulk_create methods
element_repo.bulk_create_wall_shears(shear_objects)  # AttributeError!
```

**Element Dictionary Pattern**:
Pre-create all elements before processing rows (like data_importer.py):
```python
# 1. Create element dictionary upfront with CORRECT element type
pier_elements = {}
for pier_name in piers:
    element = element_repo.get_or_create(
        project_id=project_id,
        element_type="Wall",  # Use "Wall" for pier forces/shears
        unique_name=pier_name,
        name=pier_name,
    )
    pier_elements[pier_name] = element

# For quad rotations, use element_type="Quad"
quad_elements = {}
for quad_name in quads:
    element = element_repo.get_or_create(
        project_id=project_id,
        element_type="Quad",  # NOT "Wall" - quads are separate!
        unique_name=quad_name,
        name=quad_name,
    )
    quad_elements[quad_name] = element

# 2. Look up during processing
for _, row in processed.iterrows():
    element = pier_elements[row["Pier"]]  # Direct dict lookup
```

**Column Name Consistency**:
DataFrames use spaces in column names (from Excel parser):
- ✅ `df['Output Case']` - Correct (with space)
- ❌ `df['OutputCase']` - Wrong (causes KeyError)
- ✅ `column_name = "Ux"` or `"Uy"` - Lowercase x/y
- ❌ `direction = "UX"` or `"UY"` - Wrong in ResultProcessor call

**Field Name Mapping**:
Database models use specific field names:
- `WallShear`, `ColumnShear`: Use `force`, `max_force`, `min_force` (NOT shear)
- `ColumnAxial`: Use `force`, `min_force` (NOT axial)
- `BeamRotation`: Use `R3Plastic`, `MaxR3Plastic`, `MinR3Plastic` (NOT Rotation)

### Extension Points

**Adding New Result Types**:
SelectiveDataImporter automatically supports new result types by following the same pattern:
```python
def _import_new_result_type(self, session, project_id: int) -> dict:
    # 1. Get data
    df, load_cases, ... = self.parser.get_new_result_type()

    # 2. Filter load cases
    filtered_cases = self._filter_load_cases(load_cases)
    if not filtered_cases:
        return stats

    # 3. Filter dataframe with CORRECT column name
    df = df[df['Output Case'].isin(filtered_cases)].copy()  # Note: space!

    # 4. For elements: Pre-create element dictionary
    if is_element_result:
        element_dict = {}
        for elem_name in element_names:
            elem = element_repo.get_or_create(...)
            element_dict[elem_name] = elem

    # 5. Process and use session.bulk_save_objects()
    session.bulk_save_objects(objects)
    session.commit()
```

**Custom Selection Strategies**:
Future enhancements could add:
- Saved selection presets ("DES only", "MCE + SLE", etc.)
- Load case pattern matching with regex
- Date-based filtering (import only recent runs)
- Auto-conflict resolution strategies (newest file, largest file, etc.)

---

## 9. Data Flow

### Import Pipeline (Standard Folder Batch)
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

### Enhanced Import Pipeline (With Load Case Selection)
```
1. User browses folder, enables enhanced import
   ↓
2. Pre-scan phase:
   → Discover all .xlsx/.xls files
   → Parse each file to extract load case names
   → Build map: file → sheet → load_cases
   ↓
3. Load Case Selection Dialog:
   → Display all discovered load cases in table
   → User filters/searches load cases
   → User selects desired cases (deselect test/preliminary)
   → User clicks OK (or Cancel to abort)
   ↓
4. Conflict Detection:
   → Check if same load case appears in multiple files
   → For selected load cases only
   → Build conflict map: load_case → [file1, file2, ...]
   ↓
5. Conflict Resolution Dialog (if conflicts exist):
   → Display conflicts with radio buttons
   → User chooses which file to use for each conflict
   → Or skips conflicting load cases
   → User clicks OK (or Cancel to abort)
   ↓
6. Selective Import:
   → For each file:
     → Parse Excel (pandas)
     → Filter dataframe to only selected load cases
     → Filter out conflicting cases (unless this file was chosen)
     → Transform data (ResultTransformer)
     → Bulk insert to database
     → Update progress
   ↓
7. Generate wide-format cache
   ↓
8. Refresh UI
```

**Key Differences**:
- **Standard**: Imports all load cases from all files, last-write-wins for conflicts
- **Enhanced**: User controls which load cases to import, resolves conflicts explicitly
- **Use Cases for Enhanced**:
  - Multiple files with split load cases (efficiency)
  - Filtering out test/preliminary cases
  - Explicit conflict resolution

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

## 9.5. Result Service Architecture

### Modular Package Design (v1.6 Refactor)

The `result_service` has been refactored from a monolithic 1100+ line file into a modular package with focused responsibilities:

**Package Structure**:
```
processing/result_service/
├── __init__.py           # Public API (re-exports main classes)
├── service.py            # ResultDataService facade (457 lines)
├── models.py             # Data models (39 lines)
├── cache_builder.py      # Standard/element dataset builders (164 lines)
├── maxmin_builder.py     # Max/min dataset builders (203 lines)
├── metadata.py           # Display label utilities (29 lines)
└── story_loader.py       # StoryProvider caching helper (34 lines)
```

**Core Components**:

1. **ResultDataService (`service.py`)**
   - **Purpose**: Facade coordinating data retrieval and caching
   - **Responsibilities**:
     - Standard datasets (drifts, accelerations, forces, etc.)
     - Element datasets (wall shears, column shears, etc.)
     - Max/min envelope datasets
     - All rotation/beam datasets for scatter plots
     - In-memory caching with invalidation
   - **Dependencies**: Cache repos, story repo, load case repo, element repo
   - **Caching Strategy**: Three separate caches (standard, maxmin, element) with tuple keys

2. **Data Models (`models.py`)**
   - **ResultDatasetMeta**: Immutable metadata (result_type, direction, result_set_id, display_name)
   - **ResultDataset**: Complete dataset with data, config, load case columns, summary columns
   - **MaxMinDataset**: Envelope data with directions and source type

3. **Cache Builders (`cache_builder.py`)**
   - **build_standard_dataset()**: Global results (drifts, accelerations, etc.)
     - Queries `GlobalResultsCache`
     - Applies transformers
     - Handles sheet-specific story ordering
     - Adds statistics (Avg, Max, Min)
   - **build_element_dataset()**: Element-specific results (wall/column shears, etc.)
     - Queries `ElementResultsCache`
     - Similar pipeline to standard datasets
     - Element-scoped data

4. **Max/Min Builders (`maxmin_builder.py`)**
   - **build_drift_maxmin_dataset()**: Drift envelopes
     - Uses `AbsoluteMaxMinDrift` table
     - Absolute max/min across both directions
   - **build_generic_maxmin_dataset()**: Other result envelopes
     - Generic builder for accelerations, forces, displacements
     - Queries raw result tables directly
     - Computes absolute max/min on the fly

5. **Story Provider (`story_loader.py`)**
   - **Purpose**: Centralized story metadata caching
   - **Benefits**: Avoid repeated queries, consistent story ordering
   - **Usage**: Shared across all dataset builders

6. **Metadata Utilities (`metadata.py`)**
   - **build_display_label()**: User-facing result names
   - **DISPLAY_NAME_OVERRIDES**: Mapping of internal to display names

**Import Strategy (Backward Compatible)**:
```python
# Old import (still works)
from processing.result_service import ResultDataService, ResultDataset

# New imports (also work)
from processing.result_service.service import ResultDataService
from processing.result_service.models import ResultDataset, MaxMinDataset
from processing.result_service.cache_builder import build_standard_dataset
```

**Benefits of Refactor**:
- **Single Responsibility**: Each module has one clear purpose
- **Testability**: Easy to test individual builders with mocks/stubs
- **Maintainability**: Smaller files (~200 lines max vs 1100+ lines)
- **Separation of Concerns**: Models, builders, and service logic separated
- **No Breaking Changes**: `__init__.py` re-exports maintain backward compatibility

**Usage Example**:
```python
# UI layer creates service once
service = ResultDataService(
    project_id=1,
    cache_repo=cache_repo,
    story_repo=story_repo,
    load_case_repo=load_case_repo,
    abs_maxmin_repo=abs_maxmin_repo,
    element_cache_repo=element_cache_repo,
    element_repo=element_repo,
    session=session,
)

# Fetch standard dataset (with caching)
dataset = service.get_standard_dataset("Drifts", "X", result_set_id=42)

# Fetch max/min envelope
maxmin = service.get_maxmin_dataset(result_set_id=42, base_result_type="Drifts")

# Fetch element dataset
element_ds = service.get_element_dataset(element_id=5, result_type="WallShears",
                                         direction="V2", result_set_id=42)

# Invalidate cache when data changes
service.invalidate_all()
```

---

## 10. Extension Points

### Adding New View Type (Widget)

**Example: Custom Comparison View**

```python
# 1. Create new widget (gui/comparison_view.py)
class ComparisonView(QWidget):
    """Compare multiple result sets side by side."""

    def __init__(self, parent=None):
        super().__init__(parent)
        # Setup UI with your custom layout
        ...

    def load_datasets(self, datasets: list[ResultDataset]):
        """Load multiple datasets for comparison."""
        ...

    def clear(self):
        """Reset the view."""
        ...

# 2. Add to ProjectDetailWindow
class ProjectDetailWindow(QMainWindow):
    def __init__(self, context):
        ...
        # Create widget
        self.comparison_view = ComparisonView()
        self.comparison_view.hide()
        layout.addWidget(self.comparison_view)

    def on_browser_selection_changed(self, ...):
        # Add case for new view type
        if result_type == "Comparison":
            self.standard_view.hide()
            self.maxmin_widget.hide()
            self.all_rotations_widget.hide()
            self.comparison_view.show()  # Show new widget
            self.load_comparison_data(...)

# Done! New view type integrated.
```

**Key Points**:
- Create widget with `load_*()` and `clear()` methods
- Add widget to content area layout in `ProjectDetailWindow`
- Add show/hide logic in `on_browser_selection_changed()`
- Add data loading method if needed

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
| **StandardResultView pattern** | Reusable component, consistent wiring | Slightly less flexible than inline |
| **View orchestration** | Easy to add new view types | More widgets in memory (but hidden) |
| **Window utilities extraction** | Platform-specific code isolated | Extra file to maintain |
| **Result service modularization** | Focused modules (~200 lines each), testable components, single responsibility | More files to navigate (6 modules vs 1 file) |

---

**Document Revision History**

| Version | Date | Changes |
|---------|------|---------|
| 1.9 | 2024-11-07 | Element type separation fix (Quad vs Wall), per-sheet conflict resolution, project structure cleanup (docs/ folder), cache generation fixes |
| 1.8 | 2024-11-06 | Import dialog UI refinement (dynamic borders, classic checkboxes, compact layout), conflict dialog redesign (split panels) |
| 1.7 | 2024-11-05 | Async import UI (background threading), smart data detection, browser UX optimization, layout optimization |
| 1.6 | 2024-11-01 | Result service modularization: Refactored monolithic `result_service.py` (1117 lines) into focused package with 6 modules (service, models, cache_builder, maxmin_builder, metadata, story_loader). Added comprehensive testing. Backward compatible imports. |
| 1.5 | 2024-11-01 | Major UI refactor: StandardResultView pattern, view orchestration, window utilities, project structure reorganization |
| 1.4.1 | 2024-10-27 | All Rotations scatter plot, quad rotation global ordering exception, cache entry tuple fix |
| 1.4 | 2024-10-27 | Element results (WallShears, QuadRotations), sheet-specific story ordering (story_sort_order), directionless results support, ElementResultsCache |
| 1.3 | 2024-10-25 | Catalog/per-project DB split, ResultImportHelper, shared visual config/legend components, project_tools CLI |
| 1.2 | 2024-10-24 | Condensed to ~600 lines, removed redundancy |
| 1.1 | 2024-10-24 | Added interactive features, plot configuration |
| 1.0 | 2024-10-23 | Initial consolidated architecture doc |

---

**Related Documents**

Core Documentation:
- `PRD.md` - Product requirements and features
- `CLAUDE.md` - Development guide and code examples
- `DESIGN.md` - Visual design system and UI guidelines
- `README.md` - Project overview and setup

Additional Documentation:
- `docs/fixes/` - Bug fix documentation and debugging notes
- `docs/implementation/` - Feature implementation guides
- `docs/README.md` - Documentation index
