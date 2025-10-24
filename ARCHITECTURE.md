# Architecture Documentation
## Results Processing System (RPS)

**Version**: 1.2
**Last Updated**: 2025-10-24
**Status**: Production-ready with refactored architecture

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
├── gui/
│   ├── styles.py                 # GMP design system
│   ├── main_window.py            # Project cards view
│   ├── project_detail_window.py  # 3-panel layout (browser|table|plot)
│   ├── results_table_widget.py   # Compact table display
│   └── results_plot_widget.py    # PyQtGraph building profiles
├── processing/
│   ├── excel_parser.py           # Excel file reading
│   ├── result_transformers.py    # Pluggable transformers
│   ├── data_importer.py          # Single file → DB pipeline
│   └── folder_importer.py        # Batch folder → DB pipeline
├── database/
│   ├── models.py                 # ORM models (hybrid schema)
│   └── repository.py             # Data access layer (CRUD)
└── utils/
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

### Core Schema

**Projects** → **ResultSets** → **GlobalResultsCache** (wide-format JSON)
**Projects** → **Stories** + **LoadCases** → **StoryDrift/Acceleration/Force** (normalized)

**GlobalResultsCache** (Performance-optimized):
```python
project_id: FK → projects.id
result_set_id: FK → result_sets.id
result_type: String('Drifts', 'Accelerations', 'Forces')
story_id: FK → stories.id
results_matrix: JSON  # {"TH01": 0.0123, "TH02": 0.0145, ...}
```

### Indexing Strategy
- Composite indexes on `(project_id, name)` for uniqueness
- Composite indexes on `(story_id, load_case_id, direction)` for result queries
- Cache indexes on `(project_id, result_set_id, result_type)`

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
    # ... more configs
}

def get_config(result_type: str) -> ResultTypeConfig:
    return RESULT_CONFIGS.get(result_type, RESULT_CONFIGS['Drifts'])
```

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
    └─> Status Bar
```

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

---

**Document Revision History**

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2025-10-23 | Initial consolidated architecture doc |
| 1.1 | 2025-10-24 | Added interactive features, plot configuration |
| 1.2 | 2025-10-24 | Condensed to ~600 lines, removed redundancy |

---

**Related Documents**
- `PRD.md` - Product requirements and features
- `CLAUDE.md` - Development guide and code examples
- `README.md` - Project overview and setup
