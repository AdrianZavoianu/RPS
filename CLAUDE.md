# CLAUDE.md - Quick Development Guide

**RPS (Results Processing System)** - Structural engineering results processor (ETABS/SAP2000)
**Stack**: PyQt6 + PyQtGraph + SQLite + SQLAlchemy + Pandas
**Status**: Production-ready (v2.22 - January 2025)

---

## Documentation Structure
- **CLAUDE.md** (this file): Quick development tasks
- **ARCHITECTURE.md**: Technical architecture, data model, patterns
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
```python
# config/result_config.py - Add new result type in ~10 lines
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

### Registry Pattern (v2.22)
```python
# Use PushoverRegistry for lazy loading importers/parsers
from processing import get_pushover_importer, get_pushover_parser
importer_cls = get_pushover_importer("beam")
parser_cls = get_pushover_parser("soil_pressure")
```

### Data Model (27 tables)
- **Catalog**: CatalogProject
- **Core**: Project, Story, LoadCase, ResultSet, ComparisonSet, Element
- **Global Results**: StoryDrift, StoryAcceleration, StoryForce, StoryDisplacement
- **Element Results**: WallShear, QuadRotation, ColumnShear, ColumnAxial, ColumnRotation, BeamRotation
- **Foundation**: SoilPressure, VerticalDisplacement
- **Pushover**: PushoverCase, PushoverCurvePoint
- **Cache**: GlobalResultsCache, ElementResultsCache, JointResultsCache, AbsoluteMaxMinDrift, TimeSeriesGlobalCache

---

## Key File Locations

### Configuration
- `config/result_config.py` - Result type definitions
- `config/visual_config.py` - Colors, styling

### Data Access
- `database/models.py` - All ORM models
- `database/repositories/` - Domain repositories (project, story, element, cache, etc.)
- `database/base_repository.py` - Generic CRUD operations
- `processing/result_service/` - Data retrieval layer (service.py, providers.py, cache_builder.py)

### Import System
- `services/import_preparation.py` - Prescan service with parallel scanning
- `processing/enhanced_folder_importer.py` - Main import with conflict resolution
- `processing/excel_parser.py` - Excel sheet parsing
- `processing/result_transformers.py` - Data transformation
- `processing/pushover_registry.py` - Centralized pushover importer/parser registry

### UI
- `gui/project_detail/` - Project detail window (window.py, view_loaders.py, event_handlers.py)
- `gui/tree_browser/` - Results tree browser (browser.py, nltha_builders.py, pushover_builders.py)
- `gui/result_views/` - View widgets (standard_view.py, comparison_view.py, pushover_curve_view.py)
- `gui/export/` - Export dialogs and workers
- `gui/reporting/` - PDF report generation (report_window.py, pdf_generator.py)
- `gui/styles.py` - Design system constants

### Utilities
- `utils/color_utils.py` - Gradient colors
- `utils/plot_builder.py` - Declarative plotting
- `utils/pushover_utils.py` - Shorthand mapping, direction detection

---

## Common Tasks

### Export System
- **Context-Aware**: Filters by NLTHA/Pushover tab automatically
- **Multi-Format**: Combined Excel or Per-File (Excel/CSV)
- **Multi-Result-Set**: Export multiple result sets with single timestamp
- Location: `gui/export/dialogs.py`, `services/export_service.py`

### Import System
- **Folder Import**: Batch import with load case selection, conflict resolution
- **Foundation Support**: Shared foundation joint list from Fou sheet
- Location: `gui/dialogs/import_/folder_import_dialog.py`

### Pushover Analysis
**Import Workflow** (must follow order):
1. Import Pushover Curves first → Creates result set
2. Import Global Results → Select existing result set

**Key Points**:
- Direction from Output Case NAME (regex: `[_/]{direction}[+-]`)
- Joints imported automatically with global results
- Result types use `_Min` suffix: `SoilPressures_Min`, `VerticalDisplacements_Min`

### Time-Series Analysis
1. Create result set via "Load NLTHA Data"
2. Click "Load Time Series" in NLTHA tab
3. Select existing result set, browse to Excel files
4. Animated view shows 4 building profiles + base acceleration

### Comparison System
- Compare multiple result sets (DES vs MCE vs SLE)
- Supports Global, Element, and Joint results
- Ratio columns show last/first (e.g., MCE/DES = 1.68)
- Location: `gui/comparison_set_dialog.py`, `processing/result_service/comparison_builder.py`

### Adding UI Components
Follow DESIGN.md:
- Colors: `COLORS['card']` (#161b22), `COLORS['accent']` (#4a7d89)
- Spacing: 4px increments
- Use `create_styled_button()`, `create_styled_label()` from `ui_helpers.py`

---

## Story Ordering

- **Global order**: `Story.sort_order` from Story Drifts sheet
- **Per-result order**: `<result>.story_sort_order` preserves Excel row order
- **Time-series**: Query `.desc()` on `story_sort_order` (ETABS exports top-to-bottom)

---

## Troubleshooting

- **"No such table"**: `pipenv run alembic upgrade head`
- **Import fails**: Check sheet names (case-sensitive): "Story Drifts", "Pier Forces", etc.
- **Dark title bar**: Requires Windows 10+ (WSL shows light bar)
- **Cache issues**: Delete `src/**/__pycache__` and restart
- **File in use errors**: Engine disposal handled automatically on window close

---

## Platform Notes

- **Target**: Windows 10/11
- **Development**: Windows recommended (full dark theme support)
- **Deployment**: Standalone .exe via PyInstaller

---

**Last Updated**: 2025-01-23
**Version**: 2.22
