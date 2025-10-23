# Architecture Documentation
## Results Processing System (RPS)

**Version**: 1.0
**Last Updated**: 2025-10-23
**Status**: Production implementation with modern refactored architecture

---

## Table of Contents

1. [System Overview](#1-system-overview)
2. [Architecture Principles](#2-architecture-principles)
3. [Technology Stack](#3-technology-stack)
4. [Project Structure](#4-project-structure)
5. [Data Architecture](#5-data-architecture)
6. [Component Architecture](#6-component-architecture)
7. [Data Flow](#7-data-flow)
8. [Configuration System](#8-configuration-system)
9. [UI Architecture](#9-ui-architecture)
10. [Performance Optimization](#10-performance-optimization)
11. [Extension Points](#11-extension-points)
12. [Development Patterns](#12-development-patterns)

---

## 1. System Overview

### 1.1 Architecture Type

RPS follows a **layered desktop application architecture** with clear separation of concerns:

- **Presentation Layer**: PyQt6 UI components
- **Business Logic Layer**: Data processors and transformers
- **Data Access Layer**: SQLAlchemy ORM repositories
- **Data Storage Layer**: SQLite database with hybrid schema

### 1.2 Key Architectural Characteristics

- **Configuration-Driven**: Result types defined declaratively
- **Pluggable Transformers**: Strategy pattern for data processing
- **Hybrid Data Model**: Normalized + denormalized cache for performance
- **Component-Based UI**: Reusable widgets with signal/slot communication
- **Hot-Reload Development**: Web-style auto-restart on file changes

---

## 2. Architecture Principles

### 2.1 SOLID Principles

**Single Responsibility**
- Each class/module has one reason to change
- `ResultTransformer` handles only data transformation
- `PlotBuilder` handles only plot configuration
- `Repository` handles only data access

**Open/Closed Principle**
- Extend via configuration and subclassing, not modification
- Add new result types by creating config + transformer subclass
- No changes to existing code needed for extension

**Liskov Substitution**
- All transformers inherit from `ResultTransformer` base
- Any transformer can be used interchangeably via `get_transformer()`

**Interface Segregation**
- Narrow interfaces for specific purposes
- `PlotBuilder` methods are focused and independent
- Color utilities separated from data utilities

**Dependency Inversion**
- High-level components depend on abstractions
- UI depends on transformer interface, not concrete implementations
- Configuration injected, not hardcoded

### 2.2 Design Patterns

| Pattern | Usage | Location |
|---------|-------|----------|
| **Strategy** | Pluggable data transformers | `processing/result_transformers.py` |
| **Builder** | Declarative plot construction | `utils/plot_builder.py` |
| **Repository** | Data access abstraction | `database/repository.py` |
| **Factory** | Config and transformer creation | `config/result_config.py` |
| **Observer** | Qt signals/slots for UI events | All GUI components |
| **Singleton** | Database session factory | `database/base.py` |

---

## 3. Technology Stack

### 3.1 Core Technologies

| Component | Technology | Version | Purpose |
|-----------|-----------|---------|---------|
| **Language** | Python | 3.11.3 | Application logic |
| **UI Framework** | PyQt6 | Latest | Desktop GUI |
| **Visualization** | PyQtGraph | Latest | High-performance plotting |
| **Database** | SQLite | 3.x | Local data storage |
| **ORM** | SQLAlchemy | 2.x | Database abstraction |
| **Migrations** | Alembic | Latest | Schema versioning |
| **Data Processing** | Pandas | Latest | Excel parsing, transformations |
| **Package Mgmt** | Pipenv | Latest | Dependency management |
| **Hot Reload** | watchfiles | Latest | Development auto-restart |

### 3.2 Development Tools

| Tool | Purpose |
|------|---------|
| **pytest** | Unit testing |
| **black** | Code formatting |
| **flake8** | Linting |
| **PyInstaller** | Executable building |

### 3.3 Platform Support

- **Primary**: Windows 10/11
- **Development**: Windows, WSL2, Linux
- **Deployment**: Windows .exe via PyInstaller

---

## 4. Project Structure

```
RPS/
├── src/                           # Application source code
│   ├── main.py                    # Entry point (applies global theme)
│   │
│   ├── config/                    # Configuration management (NEW ✨)
│   │   ├── __init__.py           # Package marker
│   │   └── result_config.py      # Result type configurations (dataclasses)
│   │
│   ├── gui/                       # UI components (PyQt6)
│   │   ├── styles.py             # GMP design system stylesheet
│   │   ├── ui_helpers.py         # Component creation helpers
│   │   ├── window_utils.py       # Windows title bar utilities
│   │   ├── main_window.py        # Main window with project cards
│   │   ├── project_detail_window.py  # 3-panel layout (browser|table|plot)
│   │   ├── import_dialog.py      # Single file import
│   │   ├── folder_import_dialog.py   # Batch import with progress
│   │   ├── results_tree_browser.py   # Hierarchical navigation
│   │   ├── results_table_widget.py   # Compact table display
│   │   └── results_plot_widget.py    # PyQtGraph building profiles
│   │
│   ├── processing/               # Business logic
│   │   ├── excel_parser.py       # Excel file reading
│   │   ├── result_processor.py   # Legacy data transformations
│   │   ├── result_transformers.py # Pluggable transformers (NEW ✨)
│   │   ├── data_importer.py      # Single file → DB pipeline
│   │   └── folder_importer.py    # Batch folder → DB pipeline
│   │
│   ├── database/                 # Data layer
│   │   ├── base.py              # SQLAlchemy setup, session factory
│   │   ├── models.py            # ORM models (hybrid schema)
│   │   └── repository.py        # Data access layer (CRUD operations)
│   │
│   └── utils/                   # Helper functions (NEW ✨)
│       ├── color_utils.py       # Gradient color interpolation
│       ├── data_utils.py        # Parsing and formatting helpers
│       └── plot_builder.py      # Declarative plot construction
│
├── alembic/                     # Database migrations
│   ├── env.py                   # Alembic configuration
│   └── versions/                # Migration scripts
│
├── data/                        # SQLite database files (gitignored)
│   └── rps.db                   # Main database (auto-created)
│
├── resources/                   # UI assets
│   ├── ui/                      # Qt Designer files (future)
│   └── icons/                   # Application icons (future)
│
├── tests/                       # Unit tests
│   ├── conftest.py             # pytest configuration
│   ├── test_database.py        # Database/repository tests
│   └── test_excel_parser.py    # Parser tests
│
├── Old_scripts/                # Legacy processing scripts (reference)
├── Typical Input/              # Sample Excel files for testing
│
├── Pipfile                     # Dependency declarations
├── Pipfile.lock               # Locked dependency versions
├── dev_watch.py               # Hot-reload development server
│
├── PRD.md                     # Product requirements
├── ARCHITECTURE.md            # This file
├── CLAUDE.md                  # Development guide
└── README.md                  # Project overview
```

---

## 5. Data Architecture

### 5.1 Hybrid Data Model

RPS uses a **hybrid normalized + denormalized** approach:

- **Normalized tables**: Maintain data integrity and relationships
- **Wide-format cache**: Optimize for fast tabular display
- **Best of both worlds**: Reliable storage + high performance

### 5.2 Database Schema

#### Core Models

**Projects** (`projects`)
```python
id: Integer (PK)
name: String(255) UNIQUE
description: Text
created_at: DateTime
updated_at: DateTime
```

**LoadCases** (`load_cases`)
```python
id: Integer (PK)
project_id: Integer (FK → projects.id)
name: String(100)
case_type: String(50)  # 'Time History', 'Modal', 'Static'
description: Text

INDEX: (project_id, name) UNIQUE
```

**Stories** (`stories`)
```python
id: Integer (PK)
project_id: Integer (FK → projects.id)
name: String(100)
elevation: Float
sort_order: Integer

INDEX: (project_id, name) UNIQUE
```

**ResultSets** (`result_sets`)
```python
id: Integer (PK)
project_id: Integer (FK → projects.id)
name: String(100)  # 'DES', 'MCE', etc.
result_category: String(50)  # 'Envelopes', 'Time-Series'
description: Text
created_at: DateTime

INDEX: (project_id, name) UNIQUE
```

#### Normalized Result Storage

**StoryDrift** (`story_drifts`)
```python
id: Integer (PK)
story_id: Integer (FK → stories.id)
load_case_id: Integer (FK → load_cases.id)
direction: String(10)  # 'X' or 'Y'
drift: Float
max_drift: Float
min_drift: Float

INDEX: (story_id, load_case_id, direction)
```

**StoryAcceleration** (`story_accelerations`)
```python
id: Integer (PK)
story_id: Integer (FK → stories.id)
load_case_id: Integer (FK → load_cases.id)
direction: String(10)  # 'UX' or 'UY'
acceleration: Float  # in g-units
max_acceleration: Float
min_acceleration: Float

INDEX: (story_id, load_case_id, direction)
```

**StoryForce** (`story_forces`)
```python
id: Integer (PK)
story_id: Integer (FK → stories.id)
load_case_id: Integer (FK → load_cases.id)
direction: String(10)  # 'VX' or 'VY'
location: String(20)  # 'Top' or 'Bottom'
force: Float
max_force: Float
min_force: Float

INDEX: (story_id, load_case_id, direction)
```

#### Wide-Format Cache

**GlobalResultsCache** (`global_results_cache`)
```python
id: Integer (PK)
project_id: Integer (FK → projects.id)
result_set_id: Integer (FK → result_sets.id)
result_type: String(50)  # 'Drifts', 'Accelerations', 'Forces'
story_id: Integer (FK → stories.id)
results_matrix: JSON  # {"TH01": 0.0123, "TH02": 0.0145, ...}
last_updated: DateTime

INDEX: (project_id, result_set_id, result_type)
INDEX: (story_id)
```

**JSON Format Example:**
```json
{
  "TH01": 0.0123,
  "TH02": 0.0145,
  "TH03": 0.0132,
  "MCR1": 0.0098,
  "MCR2": 0.0112
}
```

#### Future Expansion Models

**Element** (`elements`) - Ready for element-level results
```python
id: Integer (PK)
project_id: Integer (FK → projects.id)
element_type: String(50)  # 'Column', 'Beam', 'Pier', 'Link'
name: String(100)
unique_name: String(100)
story_id: Integer (FK → stories.id)

INDEX: (project_id, element_type, unique_name) UNIQUE
```

**TimeHistoryData** (`time_history_data`) - Ready for time-series
```python
id: Integer (PK)
load_case_id: Integer (FK → load_cases.id)
element_id: Integer (FK → elements.id, nullable)
story_id: Integer (FK → stories.id, nullable)
result_type: String(50)
time_step: Float
value: Float
direction: String(10)

INDEX: (load_case_id, result_type)
INDEX: (element_id)
```

### 5.3 Data Relationships

```
Project (1) ─────────┬──────────> (N) LoadCase
                     │
                     ├──────────> (N) Story
                     │
                     ├──────────> (N) ResultSet ──> (N) GlobalResultsCache
                     │
                     └──────────> (N) Element (future)

LoadCase (1) ────────┬──────────> (N) StoryDrift
                     │
                     ├──────────> (N) StoryAcceleration
                     │
                     ├──────────> (N) StoryForce
                     │
                     └──────────> (N) TimeHistoryData (future)

Story (1) ───────────┬──────────> (N) StoryDrift
                     │
                     ├──────────> (N) StoryAcceleration
                     │
                     ├──────────> (N) StoryForce
                     │
                     └──────────> (N) GlobalResultsCache
```

### 5.4 Indexing Strategy

**Query Optimization:**
- Composite indexes on (project_id, name) for uniqueness
- Composite indexes on (story_id, load_case_id, direction) for result queries
- Covering indexes for cache lookups
- Foreign key indexes for join performance

**Bulk Operations:**
- Batch inserts for Excel import (100+ rows/transaction)
- Session.bulk_insert_mappings() for performance
- Transaction rollback on error

---

## 6. Component Architecture

### 6.1 Configuration System

**Location**: `src/config/result_config.py`

**Purpose**: Centralized, declarative result type definitions

**Structure**:
```python
@dataclass
class ResultTypeConfig:
    name: str
    direction_suffix: str  # Column name suffix: '_X', '_UX', '_VX'
    unit: str              # Display unit: '%', 'g', 'kN'
    decimal_places: int    # Formatting precision
    multiplier: float      # Unit conversion (e.g., 100.0 for percentage)
    y_label: str           # Plot axis label
    plot_mode: str         # 'building_profile' or future modes
    color_scheme: str      # 'blue_orange', 'green_red', etc.
```

**Registry Pattern**:
```python
RESULT_CONFIGS = {
    'Drifts': ResultTypeConfig(...),
    'Accelerations': ResultTypeConfig(...),
    'Forces': ResultTypeConfig(...),
}

def get_config(result_type: str) -> ResultTypeConfig:
    return RESULT_CONFIGS.get(result_type, RESULT_CONFIGS['Drifts'])
```

**Extension**: Add new result type in 10 lines:
```python
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
```

### 6.2 Transformer System

**Location**: `src/processing/result_transformers.py`

**Purpose**: Pluggable data transformation strategy

**Base Class**:
```python
class ResultTransformer(ABC):
    def __init__(self, result_type: str):
        self.result_type = result_type
        self.config = get_config(result_type)

    @abstractmethod
    def filter_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        """Filter relevant columns (direction-specific)."""
        pass

    def clean_column_names(self, df: pd.DataFrame) -> pd.DataFrame:
        """Extract load case names from full column names."""
        # "160Wil_DES_Global_TH01_X" → "TH01"
        ...

    def add_statistics(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calculate Avg, Max, Min across load cases."""
        ...

    def transform(self, df: pd.DataFrame) -> pd.DataFrame:
        """Full pipeline: filter → clean → statistics."""
        df = self.filter_columns(df)
        df = self.clean_column_names(df)
        df = self.add_statistics(df)
        return df
```

**Concrete Implementations**:
```python
class DriftTransformer(ResultTransformer):
    def filter_columns(self, df):
        x_columns = [col for col in df.columns
                     if col.endswith(self.config.direction_suffix)]
        return df[x_columns].copy()

class AccelerationTransformer(ResultTransformer):
    def filter_columns(self, df):
        ux_columns = [col for col in df.columns
                      if col.endswith(self.config.direction_suffix)]
        return df[ux_columns].copy()

class ForceTransformer(ResultTransformer):
    def filter_columns(self, df):
        vx_columns = [col for col in df.columns
                      if col.endswith(self.config.direction_suffix)]
        return df[vx_columns].copy()
```

**Registry and Factory**:
```python
TRANSFORMERS = {
    'Drifts': DriftTransformer(),
    'Accelerations': AccelerationTransformer(),
    'Forces': ForceTransformer(),
}

def get_transformer(result_type: str) -> ResultTransformer:
    return TRANSFORMERS.get(result_type, TRANSFORMERS['Drifts'])
```

**Usage in UI**:
```python
# project_detail_window.py
transformer = get_transformer(result_type)
df = transformer.transform(df)
```

### 6.3 Utility Functions

**Color Utilities** (`src/utils/color_utils.py`)
```python
def interpolate_color(value, min_val, max_val,
                      start_color, end_color) -> QColor:
    """Linear RGB interpolation between two colors."""
    ...

COLOR_SCHEMES = {
    'blue_orange': ('#3b82f6', '#fb923c'),
    'green_red': ('#2ed573', '#e74c3c'),
    'cool_warm': ('#60a5fa', '#f87171'),
    'teal_yellow': ('#14b8a6', '#fbbf24'),
}

def get_gradient_color(value, min_val, max_val,
                       scheme='blue_orange') -> QColor:
    """Get color for value using named scheme."""
    start_color, end_color = COLOR_SCHEMES.get(scheme, COLOR_SCHEMES['blue_orange'])
    return interpolate_color(value, min_val, max_val, start_color, end_color)
```

**Data Utilities** (`src/utils/data_utils.py`)
```python
def parse_percentage_value(val) -> float:
    """Parse '1.23%' → 1.23 or 0.0123 → 1.23."""
    if isinstance(val, str) and '%' in val:
        return float(val.replace('%', ''))
    return float(val) * 100

def parse_numeric_safe(val, default: float = 0.0) -> float:
    """Safe numeric parsing with fallback."""
    try:
        return float(val)
    except (ValueError, TypeError):
        return default

def format_value(value: float, decimal_places: int, unit: str = '') -> str:
    """Format numeric value with precision and unit."""
    return f"{value:.{decimal_places}f}{unit}"
```

**Plot Builder** (`src/utils/plot_builder.py`)
```python
class PlotBuilder:
    def __init__(self, plot_widget: pg.PlotWidget, config: ResultTypeConfig):
        self.plot = plot_widget
        self.config = config

    def setup_axes(self, stories: list[str], x_label=None, y_label=None):
        """Configure axes with story labels."""
        ...

    def set_story_range(self, num_stories: int, padding: float = -0.05):
        """Set y-axis range for stories with tight fit."""
        ...

    def set_value_range(self, min_val, max_val,
                       left_padding=0.02, right_padding=0.15):
        """Set x-axis range with asymmetric padding."""
        ...

    def add_line(self, x_values, y_values, color, width=2,
                style=Qt.PenStyle.SolidLine):
        """Add a line to the plot."""
        ...

    def set_title(self, title: str, bold: bool = True):
        """Set plot title."""
        ...
```

**Usage**:
```python
# results_plot_widget.py
config = get_config(result_type)
builder = PlotBuilder(plot, config)
builder.setup_axes(stories)
builder.set_story_range(len(stories), padding=-0.05)
builder.set_value_range(min_val, max_val, left_padding=0.02, right_padding=0.15)
builder.add_line(x_values, y_values, color='#3b82f6', width=2)
builder.set_title("Story Drifts")
```

---

## 7. Data Flow

### 7.1 Import Pipeline (Single File)

```
1. User Action
   │
   ├─> File → Import Excel
   │
2. Excel Parser
   │
   ├─> Read sheets: Story Drifts, Accelerations, Forces
   ├─> Skip header rows (0, 2)
   ├─> Extract unique load cases
   ├─> Extract unique stories
   │
3. Result Processor
   │
   ├─> Calculate absolute max, max, min
   ├─> Convert units (acceleration: mm/s² → g)
   ├─> Group by story and load case
   │
4. Data Importer
   │
   ├─> Create/get project
   ├─> Bulk insert load cases
   ├─> Bulk insert stories
   ├─> Bulk insert results (drifts, accelerations, forces)
   ├─> Commit transaction
   │
5. UI Update
   │
   └─> Refresh project cards
```

### 7.2 Import Pipeline (Folder Batch)

```
1. User Action
   │
   ├─> Load Data → Browse Folder
   │
2. File Discovery
   │
   ├─> Find all .xlsx/.xls files recursively
   ├─> Display progress dialog
   │
3. Batch Processing
   │
   ├─> For each file:
   │   ├─> Parse Excel
   │   ├─> Prefix load cases with filename
   │   ├─> Import to database
   │   ├─> Update progress (file count)
   │   └─> Continue on error (log failure)
   │
4. Cache Generation
   │
   ├─> Build wide-format cache for all results
   ├─> Store in GlobalResultsCache table
   │
5. UI Update
   │
   └─> Refresh results browser
```

### 7.3 Display Pipeline

```
1. User Selection
   │
   ├─> Results Tree Browser: Select "Drifts"
   │
2. Data Retrieval
   │
   ├─> Query GlobalResultsCache for project + result_type
   ├─> Join with stories for ordering
   ├─> Return wide-format DataFrame
   │
3. Data Transformation
   │
   ├─> Get transformer: get_transformer("Drifts")
   ├─> Transform: filter columns, clean names, add statistics
   │
4. UI Display
   │
   ├─> Table Widget
   │   ├─> Format values using config (multiplier, decimals, unit)
   │   ├─> Apply gradient colors using color_utils
   │   ├─> Auto-fit table width
   │
   └─> Plot Widget
       ├─> Parse values using data_utils
       ├─> Build plot using PlotBuilder
       ├─> Render building profile
```

---

## 8. Configuration System

### 8.1 Result Type Configuration

**File**: `src/config/result_config.py`

**Adding a New Result Type**:

```python
# 1. Add configuration to RESULT_CONFIGS
RESULT_CONFIGS['JointDisplacements'] = ResultTypeConfig(
    name='JointDisplacements',
    direction_suffix='_UX',     # Column filter
    unit='mm',                   # Display unit
    decimal_places=2,            # Formatting
    multiplier=1.0,              # No conversion needed
    y_label='Displacement (mm)', # Plot axis
    plot_mode='building_profile',# Plot type
    color_scheme='blue_orange',  # Color gradient
)

# 2. Create transformer (result_transformers.py)
class JointDisplacementTransformer(ResultTransformer):
    def __init__(self):
        super().__init__('JointDisplacements')

    def filter_columns(self, df):
        ux_columns = [col for col in df.columns
                      if col.endswith(self.config.direction_suffix)]
        return df[ux_columns].copy()

# 3. Register transformer
TRANSFORMERS['JointDisplacements'] = JointDisplacementTransformer()

# Done! Configuration flows to all UI components automatically.
```

### 8.2 UI Theme Configuration

**File**: `src/gui/styles.py`

**GMP Design System Colors**:
```python
COLORS = {
    'background': '#0a0c10',  # Main background
    'card': '#161b22',        # Panels/cards
    'border': '#2c313a',      # Borders
    'text': '#d1d5db',        # Primary text
    'muted': '#7f8b9a',       # Secondary text
    'accent': '#4a7d89',      # Buttons/highlights
}
```

**Component Styling**:
```python
# src/gui/ui_helpers.py
def create_styled_button(text, variant="primary", size="md"):
    """Create button with GMP styling."""
    button = QPushButton(text)
    button.setProperty("variant", variant)
    button.setProperty("size", size)
    button.style().unpolish(button)
    button.style().polish(button)
    return button
```

---

## 9. UI Architecture

### 9.1 Window Hierarchy

```
QApplication
│
├─> MainWindow (main_window.py)
│   ├─> Header (64px fixed)
│   ├─> Project Cards Grid
│   └─> Action Buttons
│
└─> ProjectDetailWindow (project_detail_window.py)
    ├─> Header (64px fixed)
    ├─> Content Area (3-panel splitter)
    │   ├─> Results Tree Browser (200px fixed)
    │   ├─> Results Table Widget (auto-fit)
    │   └─> Results Plot Widget (remaining space)
    └─> Status Bar
```

### 9.2 Component Communication

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

**Event Flow Example (Column Selection)**:
```
1. User clicks column header in table
   ↓
2. TableWidget._on_header_clicked()
   ↓
3. Emit signal: selection_changed.emit(['TH01', 'TH02'])
   ↓
4. PlotWidget.highlight_lines(['TH01', 'TH02'])
   ↓
5. Plot updates: dim non-selected lines, highlight selected
```

### 9.3 Layout System

**Project Detail Window Layout**:
```python
main_layout = QVBoxLayout()
main_layout.setContentsMargins(0, 0, 0, 0)
main_layout.setSpacing(0)

# Header (fixed 64px)
main_layout.addWidget(header)

# Content area (splitter)
content_layout = QHBoxLayout()
content_layout.setContentsMargins(16, 8, 16, 8)  # Padding around splitter

splitter = QSplitter(Qt.Orientation.Horizontal)
splitter.setHandleWidth(8)
splitter.setStyleSheet("QSplitter::handle { background: transparent; }")

# Browser (fixed 200px)
splitter.addWidget(results_browser)
splitter.setStretchFactor(0, 0)

# Table (auto-fit width)
splitter.addWidget(table_widget)
splitter.setStretchFactor(1, 0)

# Plot (remaining space)
splitter.addWidget(plot_widget)
splitter.setStretchFactor(2, 1)

content_layout.addWidget(splitter)
main_layout.addLayout(content_layout)
```

**Table Auto-Fit Logic**:
```python
# results_table_widget.py
story_column_width = 70  # "Story 1"
data_column_width = 55   # "0.00%"

total_width = story_column_width + (len(df.columns) - 1) * data_column_width + 2

self.table.setMinimumWidth(total_width)
self.table.setMaximumWidth(total_width)
self.setMinimumWidth(total_width)
self.setMaximumWidth(total_width)
```

---

## 10. Performance Optimization

### 10.1 Database Performance

**Bulk Inserts**:
```python
# repository.py
def bulk_create_drifts(self, drift_data: list[dict]):
    """Bulk insert for 100+ rows in single transaction."""
    session.bulk_insert_mappings(StoryDrift, drift_data)
    session.commit()
```

**Indexed Queries**:
```python
# Fast lookups via composite indexes
INDEX: (project_id, result_set_id, result_type)
INDEX: (story_id, load_case_id, direction)
```

**Wide-Format Cache**:
```python
# No JOIN queries needed for display
# Single query returns all load cases for a story
cache_entry = session.query(GlobalResultsCache).filter_by(
    project_id=project_id,
    result_type='Drifts',
).all()
```

### 10.2 UI Performance

**PyQtGraph Optimization**:
- GPU-accelerated rendering (OpenGL backend)
- Supports 100k+ data points
- Fast pen and brush caching
- Efficient update methods (setData, not recreate)

**Table Rendering**:
- Fixed column widths (no dynamic resizing)
- Batch item creation in single loop
- Pre-calculated gradients (color utilities)
- Disabled horizontal scrolling

**Hot-Reload Development**:
```python
# dev_watch.py
watch(
    "src",
    on_change=lambda: restart_app(),
    watch_filter=lambda _, path: path.endswith('.py')
)
```

### 10.3 Memory Management

**Session Management**:
```python
# base.py
session_factory = sessionmaker(bind=engine)

def get_session():
    session = session_factory()
    try:
        yield session
    finally:
        session.close()
```

**DataFrame Operations**:
```python
# Always use .copy() to avoid SettingWithCopyWarning
def filter_columns(self, df):
    x_columns = [col for col in df.columns if col.endswith('_X')]
    return df[x_columns].copy()  # Explicit copy
```

---

## 11. Extension Points

### 11.1 Adding New Result Types

**Minimal Code Required (10-15 lines)**:

```python
# 1. Configuration (result_config.py)
RESULT_CONFIGS['NewType'] = ResultTypeConfig(...)  # 8 lines

# 2. Transformer (result_transformers.py)
class NewTypeTransformer(ResultTransformer):
    def filter_columns(self, df):
        return df[[col for col in df.columns if col.endswith('_NX')]].copy()

# 3. Register (result_transformers.py)
TRANSFORMERS['NewType'] = NewTypeTransformer()  # 1 line
```

**No changes needed in**:
- UI components (table, plot)
- Data flow logic
- Formatting logic
- Color application

### 11.2 Adding New Plot Types

**Current**: `building_profile` (horizontal bar chart)

**Future**: Add to `plot_mode` config:
- `time_series` - Time vs. Value line plots
- `story_comparison` - Multi-story comparison charts
- `envelope_curve` - Max/min envelope visualization

**Implementation**:
```python
# results_plot_widget.py
def load_data(self, df, result_type):
    config = get_config(result_type)
    if config.plot_mode == 'building_profile':
        self._plot_building_profile(df, result_type)
    elif config.plot_mode == 'time_series':  # NEW
        self._plot_time_series(df, result_type)
    elif config.plot_mode == 'envelope_curve':  # NEW
        self._plot_envelope_curve(df, result_type)
```

### 11.3 Adding New Color Schemes

```python
# color_utils.py
COLOR_SCHEMES['custom_scheme'] = ('#start_color', '#end_color')

# result_config.py
RESULT_CONFIGS['ResultType'].color_scheme = 'custom_scheme'
```

### 11.4 Database Schema Extensions

**Add New Table**:
```python
# models.py
class NewResultType(Base):
    __tablename__ = "new_results"
    id = Column(Integer, primary_key=True)
    # ... fields ...

# Create migration
$ pipenv run alembic revision --autogenerate -m "Add new result type"
$ pipenv run alembic upgrade head
```

**Add to Repository**:
```python
# repository.py
def bulk_create_new_results(self, data: list[dict]):
    session.bulk_insert_mappings(NewResultType, data)
    session.commit()
```

---

## 12. Development Patterns

### 12.1 Coding Conventions

**Type Hints**:
```python
def parse_percentage_value(val) -> float:
    """Parse percentage value from string or numeric."""
    ...
```

**Docstrings** (Google Style):
```python
def interpolate_color(value: float, min_val: float, max_val: float,
                      start_color: str, end_color: str) -> QColor:
    """
    Interpolate RGB color between two colors.

    Args:
        value: Current value
        min_val: Minimum value in range
        max_val: Maximum value in range
        start_color: Starting color (hex or name)
        end_color: Ending color (hex or name)

    Returns:
        QColor interpolated between start and end
    """
    ...
```

**Error Handling**:
```python
try:
    value = float(val)
except (ValueError, TypeError):
    value = default_value
```

### 12.2 Testing Patterns

**Unit Tests** (pytest):
```python
def test_parse_percentage_value():
    assert parse_percentage_value("1.23%") == 1.23
    assert parse_percentage_value(0.0123) == 1.23
    assert parse_percentage_value("invalid") == 0.0
```

**Database Tests**:
```python
@pytest.fixture
def test_db():
    """Create in-memory test database."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    yield session
    session.close()

def test_create_project(test_db):
    project = Project(name="Test", description="Test project")
    test_db.add(project)
    test_db.commit()
    assert project.id is not None
```

### 12.3 Migration Workflow

```bash
# 1. Modify models.py
class Project(Base):
    new_field = Column(String(100))  # Added

# 2. Generate migration
$ pipenv run alembic revision --autogenerate -m "Add new_field to projects"

# 3. Review generated migration in alembic/versions/

# 4. Apply migration
$ pipenv run alembic upgrade head

# 5. Rollback if needed
$ pipenv run alembic downgrade -1
```

### 12.4 Hot-Reload Development

```bash
# Start with auto-reload
$ pipenv run python dev_watch.py

# Edit any .py file in src/
# → Application restarts automatically on save
# → Fast iteration without manual restarts
```

---

## Appendix A: Key Architectural Decisions

| Decision | Rationale | Trade-offs |
|----------|-----------|------------|
| **Hybrid data model** | Fast tabular display + data integrity | Slightly more complex schema |
| **Configuration-driven** | Easy to add result types | Requires learning config system |
| **PyQtGraph not Matplotlib** | 100x faster for large datasets | Fewer plot types available |
| **SQLite not PostgreSQL** | Local-first, no server setup | Single-user only |
| **Pipenv not Poetry** | Consistent with team standards | Slightly slower than Poetry |
| **Desktop-only (PyQt6)** | Full platform capabilities | No web/mobile version |
| **Wide-format JSON cache** | Fast display without JOINs | Cache invalidation complexity |
| **Pluggable transformers** | Extensible without code changes | Abstract base class required |

---

## Appendix B: Performance Benchmarks

| Operation | Time | Notes |
|-----------|------|-------|
| Import 10 Excel files (100 rows each) | ~15s | Including cache generation |
| Display table (50 stories, 20 load cases) | <500ms | From cache |
| Plot building profile (20 lines) | <300ms | PyQtGraph rendering |
| Column selection update | <200ms | Immediate UI feedback |
| Database query (normalized) | ~100ms | With proper indexes |
| Database query (cache) | ~20ms | Single table, no JOINs |
| Hot-reload restart | ~3s | Full app restart |

---

## Appendix C: External Dependencies

| Package | Version | Purpose | License |
|---------|---------|---------|---------|
| PyQt6 | Latest | Desktop GUI framework | GPL/Commercial |
| PyQtGraph | Latest | High-performance plotting | MIT |
| SQLAlchemy | 2.x | Database ORM | MIT |
| Alembic | Latest | Database migrations | MIT |
| Pandas | Latest | Data processing | BSD |
| NumPy | Latest | Numerical operations | BSD |
| watchfiles | Latest | File change detection | MIT |
| pytest | Latest | Testing framework | MIT |
| black | Latest | Code formatting | MIT |

---

**Document Revision History**

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2025-10-23 | Claude Code | Initial consolidated architecture doc |

---

**Related Documents**

- `PRD.md` - Product requirements and features
- `CLAUDE.md` - Development guide and code examples
- `README.md` - Project overview and setup
