# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Quick Reference

**Documentation Structure:**
- **This file (CLAUDE.md)**: Quick development guide and common tasks
- **[ARCHITECTURE.md](ARCHITECTURE.md)**: Complete technical architecture, data model, patterns
- **[PRD.md](PRD.md)**: Product requirements, features, roadmap

---

## Project Overview

**Results Processing System (RPS)** - Desktop application for processing and visualizing structural engineering results from ETABS/SAP2000 Excel exports.

**Status**: Production-ready with refactored, extensible architecture

**Tech Stack**: PyQt6 + PyQtGraph + SQLite + SQLAlchemy + Pandas

---

## Current State

### Implemented Features ✅
- Hybrid normalized + wide-format cache data model
- Folder-based batch import with progress tracking
- Project detail view: Browser | Table | Plot (3-panel)
- Story drifts visualization with interactive column selection
- Configuration-driven architecture for easy extension
- GMP-exact design system with dark theme
- Hot-reload development environment

### Recent Refactoring ✅
**Impact**: ~180 lines of duplication eliminated, adding new result types now takes 5 minutes vs 30 minutes

- **Phase 1**: Configuration-driven transformers (`result_config.py`, `result_transformers.py`)
- **Phase 2**: Utility extraction (`color_utils.py`, `data_utils.py`)
- **Phase 3**: Plot builder (`plot_builder.py`)

### Ready for Extension
- **Accelerations**: Config exists, just load UX data
- **Forces**: Config exists, just load VX data
- **Custom Result Types**: Add config + transformer (~10 lines)

---

## Key Architecture (Quick Summary)

> **Full details**: See [ARCHITECTURE.md](ARCHITECTURE.md)

### Configuration-Driven Design
```python
# config/result_config.py - Single source of truth
RESULT_CONFIGS = {
    'Drifts': ResultTypeConfig(
        direction_suffix='_X',
        unit='%',
        multiplier=100.0,
        color_scheme='blue_orange',
        ...
    ),
}
```

### Pluggable Transformers
```python
# processing/result_transformers.py
transformer = get_transformer('Drifts')
df = transformer.transform(df)  # filter → clean → statistics
```

### Data Flow
```
Excel → FolderImporter → ResultTransformer → SQLite (normalized + cache) → Table/Plot
```

### UI Communication
```
Table Widget (signals) → Plot Widget (slots)
- Column selection → highlight_lines
- Column hover → preview_line
```

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

**Time Required**: ~10 minutes

**Step 1**: Add configuration (5 lines)
```python
# config/result_config.py
RESULT_CONFIGS['JointDisplacements'] = ResultTypeConfig(
    name='JointDisplacements',
    direction_suffix='_UX',
    unit='mm',
    decimal_places=2,
    multiplier=1.0,
    y_label='Displacement (mm)',
    plot_mode='building_profile',
    color_scheme='blue_orange',
)
```

**Step 2**: Add transformer (10 lines)
```python
# processing/result_transformers.py
class JointDisplacementTransformer(ResultTransformer):
    def __init__(self):
        super().__init__('JointDisplacements')

    def filter_columns(self, df):
        cols = [col for col in df.columns if col.endswith(self.config.direction_suffix)]
        return df[cols].copy()

TRANSFORMERS['JointDisplacements'] = JointDisplacementTransformer()
```

**Step 3**: Load data into cache (database import)

**Done!** Table, plot, colors, and formatting all work automatically.

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
def set_value_range(self, min_val, max_val, left_padding=0.05, right_padding=0.20):
    # Adjust padding values
    ...

# results_plot_widget.py - Adjust plot-specific logic
def _plot_building_profile(self, df, result_type):
    # Change line styles, colors, etc.
    ...
```

---

### Adding Database Columns

```python
# 1. Edit models.py
class Project(Base):
    new_field = Column(String(100))  # Add this

# 2. Generate migration
$ pipenv run alembic revision --autogenerate -m "Add new_field"

# 3. Review migration file in alembic/versions/

# 4. Apply migration
$ pipenv run alembic upgrade head
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

## Project Structure (Key Locations)

```
src/
├── config/
│   └── result_config.py          # Result type configurations
├── gui/
│   ├── styles.py                 # GMP design system
│   ├── project_detail_window.py  # Main UI orchestration
│   ├── results_table_widget.py   # Table with interactions
│   └── results_plot_widget.py    # PyQtGraph visualizations
├── processing/
│   ├── result_transformers.py    # Pluggable transformers
│   └── folder_importer.py        # Batch import pipeline
├── database/
│   ├── models.py                 # SQLAlchemy ORM models
│   └── repository.py             # Data access layer
└── utils/
    ├── color_utils.py            # Gradient coloring
    ├── data_utils.py             # Parsing/formatting
    └── plot_builder.py           # Declarative plotting
```

> **Full structure with descriptions**: See [ARCHITECTURE.md Section 4](ARCHITECTURE.md#4-project-structure)

---

## Utility Functions Reference

### Color Utilities
```python
from utils.color_utils import get_gradient_color

# Get interpolated color for value in range
color = get_gradient_color(value, min_val, max_val, 'blue_orange')
# Available schemes: 'blue_orange', 'green_red', 'cool_warm', 'teal_yellow'
```

### Data Utilities
```python
from utils.data_utils import parse_percentage_value, format_value, parse_numeric_safe

numeric = parse_percentage_value("1.23%")  # → 1.23
numeric = parse_percentage_value(0.0123)   # → 1.23
formatted = format_value(1.234, 2, '%')    # → "1.23%"
safe_val = parse_numeric_safe("invalid", default=0.0)  # → 0.0
```

### Plot Builder
```python
from utils.plot_builder import PlotBuilder

builder = PlotBuilder(plot_widget, config)
builder.setup_axes(story_names)
builder.set_story_range(num_stories, padding=-0.05)
builder.set_value_range(min_val, max_val, left_padding=0.02, right_padding=0.15)
builder.add_line(x_values, y_values, color='#3b82f6', width=2)
builder.set_title("Story Drifts", bold=True)
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

> **Full constraints and assumptions**: See [PRD.md Section 7](PRD.md#7-constraints-and-assumptions)

---

## Troubleshooting

### "No such table" Error
```bash
pipenv run alembic upgrade head
```

### Import Fails
- Check sheet names (case-sensitive): "Story Drifts", "Story Accelerations", "Story Forces"
- Verify column format: `<prefix>_<load_case>_<direction>`
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

## File References (line numbers)

When referencing code, use this format for easy navigation:

- Configuration: `result_config.py:134-146` (Drifts config)
- Transformer base: `result_transformers.py:8-63` (ResultTransformer class)
- Drift transformer: `result_transformers.py:65-74` (DriftTransformer)
- Plot builder: `plot_builder.py:8-108` (PlotBuilder class)
- Color gradient: `color_utils.py:41-50` (get_gradient_color function)
- Data parsing: `data_utils.py:4-19` (parse_percentage_value function)
- Project detail: `project_detail_window.py:1-300` (main orchestration)
- Table widget: `results_table_widget.py:98-356` (ResultsTableWidget class)
- Plot widget: `results_plot_widget.py:1-end` (ResultsPlotWidget class)

---

**Last Updated**: 2025-10-23
**Status**: Production-ready, refactored architecture complete
