# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Results Processing System (RPS) - A modern desktop application for processing and visualizing structural engineering results from ETABS/SAP2000 Excel exports. Built with PyQt6, featuring a dark web-style theme, database storage, and high-performance visualization.

## Current State - Enhanced UI with GMP Design System ✅

**Status**: Fully functional application with GMP-matching design system and modern UI components.

The application is a **complete skeleton** with:
- ✅ **GMP-Exact Design System** - Button variants, typography, and styling matching GMP frontend
- ✅ Modern dark bluish theme with refined components
- ✅ PyQt6 desktop application with web-style UI
- ✅ SQLite database with SQLAlchemy ORM
- ✅ Excel import functionality (Story Drifts, Accelerations, Forces)
- ✅ Results browser with hierarchical navigation
- ✅ PyQtGraph visualization framework (placeholders ready)
- ✅ Database migrations with Alembic
- ✅ Full test suite (8 tests passing)
- ✅ **UI Helper System** - Easy component creation with GMP styling
- ✅ **Windows Deployment Ready** - Dependencies updated for Python 3.11.3

**Next Steps**: Implement visualization features, add more result types, enhance UI interactions.

## Technology Stack

### Core Technologies
- **Python**: 3.11.3 (current Windows deployment target)
- **UI Framework**: PyQt6 - Modern, cross-platform desktop GUI
- **Design System**: GMP-exact styling with component variants
- **Visualization**: PyQtGraph - High-performance plotting (100k+ data points)
- **Database**: SQLite with SQLAlchemy ORM + Alembic migrations
- **Data Processing**: Pandas, NumPy (from legacy scripts)
- **Package Management**: Pipenv (Pipfile + Pipfile.lock)

### Development Tools
- **Testing**: pytest
- **Formatting**: black
- **Linting**: flake8
- **Building**: PyInstaller (for .exe distribution)

## Platform Notes

**Target Platform**: Windows 10/11 (primary users)

**Development Environment**:
- Can develop on WSL/Linux (current setup)
- **Recommended**: Develop directly on Windows for better experience
  - See exact UI/UX that users will see
  - Dark title bar only works on Windows
  - No WSL/Windows file locking issues
  - Native performance and debugging

**Important**:
- Dark Windows title bar uses `DwmSetWindowAttribute` API (Windows-only)
- On WSL/Linux, title bar will be light (X11 limitation) - this is normal
- Copy project to Windows to see full dark theme: `C:\Users\{User}\SoftDev\RPS`

## Project Structure

```
RPS/
├── src/                           # Application source code
│   ├── main.py                    # Entry point, applies theme globally
│   ├── gui/                       # UI components (PyQt6)
│   │   ├── styles.py             # GMP-exact design system stylesheet
│   │   ├── ui_helpers.py         # Component creation helpers (NEW)
│   │   ├── window_utils.py       # Windows title bar utilities
│   │   ├── main_window.py        # Main application window
│   │   ├── import_dialog.py      # Modern Excel import dialog (GMP-styled)
│   │   ├── results_browser.py    # Sidebar tree navigation
│   │   └── visualization_widget.py # PyQtGraph plotting (3 tabs)
│   ├── processing/               # Business logic
│   │   ├── excel_parser.py       # Excel file reading (refactored)
│   │   ├── result_processor.py   # Data transformations
│   │   └── data_importer.py      # Excel → Database pipeline
│   ├── database/                 # Data layer
│   │   ├── base.py              # SQLAlchemy setup, session factory
│   │   ├── models.py            # ORM models (Project, LoadCase, Story, etc.)
│   │   └── repository.py        # Data access layer (CRUD operations)
│   └── utils/                   # Helper functions
├── alembic/                     # Database migrations
│   ├── env.py                   # Alembic configuration
│   └── versions/                # Migration scripts
├── data/                        # SQLite database files (gitignored)
│   └── rps.db                   # Main database (auto-created)
├── resources/                   # UI assets
│   ├── ui/                      # Qt Designer files (future)
│   └── icons/                   # Application icons (future)
├── tests/                       # Unit tests
│   ├── conftest.py             # pytest configuration
│   ├── test_database.py        # Database/repository tests
│   └── test_excel_parser.py    # Parser tests
├── Old_scripts/                # Legacy processing scripts (reference)
├── Typical Input/              # Sample Excel files for testing
├── Pipfile                     # Dependency declarations
├── Pipfile.lock               # Locked dependency versions
├── QUICKSTART.md              # Usage guide
├── SETUP_COMPLETE.md          # Setup documentation
├── MODERN_THEME_APPLIED.md    # Theme documentation
└── CLAUDE.md                  # This file
```

## Database Schema

### Core Models (SQLAlchemy)

**Projects** (`projects`)
- Represents engineering projects
- Fields: id, name, description, created_at, updated_at
- Relationships: load_cases, stories

**LoadCases** (`load_cases`)
- Analysis cases (TH01, MCR1, etc.)
- Fields: id, project_id, name, case_type, description
- Relationships: project, story_drifts, story_accelerations, story_forces

**Stories** (`stories`)
- Building floors/levels
- Fields: id, project_id, name, elevation, sort_order
- Relationships: project, drifts, accelerations, forces

**Result Tables**
- `story_drifts` - Drift results (X/Y directions)
- `story_accelerations` - Acceleration results (UX/UY, in g-units)
- `story_forces` - Shear forces (VX/VY)
- `elements` - Structural elements (columns, beams, piers) - ready for expansion
- `time_history_data` - Time-series data - ready for expansion

**Key Features**:
- Indexed columns for fast queries
- Foreign key relationships maintain data integrity
- Bulk insert support for performance
- Migration support with Alembic

## Development Commands

### Setup

```bash
# Install dependencies
pipenv install --dev

# Run database migrations (create tables)
pipenv run alembic upgrade head

# Run the application
pipenv run python src/main.py

# Demo GMP-style components
pipenv run python test_gmp_styling.py
```

### Testing

```bash
# Run all tests
pipenv run pytest tests/ -v

# Run specific test file
pipenv run pytest tests/test_database.py -v

# Run with coverage
pipenv run pytest --cov=src tests/
```

### Code Quality

```bash
# Format code
pipenv run black src/

# Lint code
pipenv run flake8 src/
```

### Database Migrations

```bash
# Create new migration (after model changes)
pipenv run alembic revision --autogenerate -m "Description"

# Apply migrations
pipenv run alembic upgrade head

# Rollback migration
pipenv run alembic downgrade -1
```

### Building Executable

```bash
# Build standalone .exe (on Windows)
pipenv run pyinstaller src/main.py --onefile --windowed --name RPS

# Output: dist/RPS.exe
```

## GMP-Exact Design System ✨

### Color Palette (Exact Match with GMP Frontend)

```python
COLORS = {
    'background': '#0a0c10',      # Main background (var(--color-background))
    'card': '#161b22',            # Panels/cards (var(--color-card))
    'border': '#2c313a',          # Borders (var(--color-border))
    'text': '#d1d5db',            # Primary text (var(--color-text))
    'muted': '#7f8b9a',           # Secondary text (var(--color-muted))
    'accent': '#4a7d89',          # Buttons/highlights (var(--color-accent))
}
```

### GMP Component System

**Button Variants** (Matching GMP React Components):
```python
from gui.ui_helpers import create_styled_button

# Exact GMP button variants
primary_btn = create_styled_button("Save", "primary")      # bg-accent text-white
secondary_btn = create_styled_button("Cancel", "secondary") # bg-card border border-border
danger_btn = create_styled_button("Delete", "danger")      # bg-red-600 text-white
ghost_btn = create_styled_button("Close", "ghost")         # transparent hover:bg-muted/20

# GMP button sizes
small_btn = create_styled_button("OK", "primary", "sm")    # px-3 py-1.5 text-sm
large_btn = create_styled_button("Submit", "primary", "lg") # px-6 py-3 text-lg
```

**Typography System** (Matching GMP Text Hierarchy):
```python
from gui.ui_helpers import create_styled_label

header = create_styled_label("Settings", "header")         # font-size: 18px, font-weight: 600
subheader = create_styled_label("Database", "subheader")   # font-size: 16px, font-weight: 500
muted = create_styled_label("Optional", "muted")           # color: muted
small = create_styled_label("Details", "small")            # font-size: 13px
```

### Styling Architecture

**Global Stylesheet** (`src/gui/styles.py`):
- **Exact GMP Match**: All components styled to match GMP frontend
- Web-inspired design with 6px border radius (matching Tailwind)
- Focus rings and transitions matching GMP interaction patterns
- Font weights and sizes matching GMP typography scale

**UI Helper System** (`src/gui/ui_helpers.py`):
- Easy component creation with GMP styling
- Type-safe variant selection (Literal types)
- Automatic style application and refresh
- Consistent API across all components

**Enhanced Components**:
- Input fields with focus rings and transitions
- Modal dialogs with proper shadows and spacing
- Typography hierarchy with semantic variants
- Button system with hover and pressed states

**Windows Title Bar**:
- Uses Windows DWM API (`DwmSetWindowAttribute`) for dark title bar
- Only works on Windows 10 (build 19041+) and Windows 11
- Automatically applied in `MainWindow.showEvent()`

## Data Processing Pipeline

### Import Workflow

1. **User Action**: File → Import Excel
2. **File Selection**: Browse for ETABS/SAP2000 Excel file
3. **Parsing** (`excel_parser.py`):
   - Read sheets: Story Drifts, Story Accelerations, Story Forces
   - Skip header rows (0, 2)
   - Extract unique load cases and stories
4. **Processing** (`result_processor.py`):
   - Calculate absolute max, max, min for each combination
   - Convert units (accelerations: mm/s² → g)
   - Group by story and load case
5. **Storage** (`data_importer.py`):
   - Create/get project
   - Bulk insert results into database
   - Return import statistics
6. **Display**: Results browser refreshes, shows new data

### Processing Conventions

**From Legacy Scripts** (maintained for compatibility):
- **Absolute maximums**: Use `abs().max()` for critical values
- **Load cases**: TH01-TH99 (time history), MCR1-MCR6 (modal combinations)
- **Step types**: "Max" and "Min" envelope values
- **Directions**: X/Y (horizontal), Z (vertical), UX/UY (accelerations), VX/VY (forces)
- **Unit conversions**: Accelerations ÷ 9810 for g-units

**Excel Sheet Names** (expected):
- Story Drifts, Story Accelerations, Story Forces
- Joint Displacements, Joint Reactions (not yet imported)
- Element Forces - Columns/Beams/Links (not yet imported)
- Pier Forces, Hinge States (not yet imported)

## UI Components

### Main Window (`main_window.py`)
- Menu bar: File, View, Tools, Help
- Sidebar (25%): Results browser
- Main content (75%): Visualization widget
- Status bar: Project indicator
- **Shortcuts**: Ctrl+I (import), Ctrl+Q (quit), F5 (refresh)

### Import Dialog (`import_dialog.py`)
- Modern card-based layout
- File browser with auto-fill project name
- Project name + analysis type fields
- Validation (requires file + project name)
- Info card with import details

### Results Browser (`results_browser.py`)
- Tree navigation with icons
- Hierarchy: Projects → Load Cases / Results
- Bold project names, collapsed load cases
- Unicode symbols (Δ drifts, ≈ accelerations, ↕ forces)
- Emits `selection_changed` signal

### Visualization Widget (`visualization_widget.py`)
- Three tabs: Time History, Envelope, Comparison
- Dark PyQtGraph plots matching theme
- Placeholder plots ready for implementation
- Export button (not yet functional)

## Code Quality & Patterns

### Best Practices

**Separation of Concerns**:
- UI in `gui/` (no direct database access)
- Business logic in `processing/`
- Data access in `database/repository.py`
- Models separate from repositories

**Cross-Platform Compatibility**:
- Use `pathlib.Path` for all file paths
- Platform detection for Windows-specific features
- Safe fallbacks for non-Windows platforms

**Error Handling**:
- Try/except blocks in import pipeline
- User-friendly error dialogs
- Database rollback on import failure
- Graceful degradation (e.g., dark title bar on non-Windows)

**Performance**:
- Bulk inserts for large datasets
- Database indexes on query columns
- PyQtGraph for fast plotting (GPU-accelerated)
- Lazy loading patterns (future enhancement)

### Known Technical Debt

From legacy scripts:
- Hard-coded column indices (brittle)
- Limited error handling
- No docstrings/type hints in old code
- Windows path separators in legacy scripts

Modern code improvements:
- ✅ Type hints added
- ✅ Docstrings in new modules
- ✅ Proper error handling
- ✅ Cross-platform paths
- ✅ Unit tests

## Common Development Tasks

### Adding a New Result Type

1. **Database Model** (`src/database/models.py`):
   ```python
   class NewResultType(Base):
       __tablename__ = "new_results"
       # Add fields, relationships, indexes
   ```

2. **Repository Methods** (`src/database/repository.py`):
   ```python
   def create_new_result(self, ...):
       # CRUD operations
   ```

3. **Excel Parser** (`src/processing/excel_parser.py`):
   ```python
   def get_new_results(self):
       # Parse Excel sheet
   ```

4. **Processor** (`src/processing/result_processor.py`):
   ```python
   def process_new_results(df, ...):
       # Transform data
   ```

5. **Importer** (`src/processing/data_importer.py`):
   ```python
   def _import_new_results(self, session, project_id):
       # Import workflow
   ```

6. **Migration**:
   ```bash
   pipenv run alembic revision --autogenerate -m "Add new result type"
   pipenv run alembic upgrade head
   ```

### Modifying the Theme

**Colors** (`src/gui/styles.py`):
```python
COLORS = {
    'accent': '#your_color',  # Change accent color
}
```

**Stylesheet** (`src/gui/styles.py`):
```python
DARK_THEME_STYLESHEET = f"""
QPushButton {{
    /* Modify button styles */
}}
"""
```

Changes apply immediately on app restart.

### Adding UI Components

1. Create widget in `src/gui/your_widget.py`
2. Import in `main_window.py`
3. Add to layout
4. Apply theme styling
5. Connect signals/slots

## Deployment

### Windows Executable

```bash
# On Windows (in project directory)
pipenv run pyinstaller src/main.py --onefile --windowed --name RPS --icon resources/icons/app.ico
```

**Output**: `dist/RPS.exe` (standalone, ~50-100MB)

**Optional**: Create installer with NSIS or Inno Setup

### Distribution Checklist

- [ ] Test on clean Windows 10/11 machine
- [ ] Include sample Excel files in `Typical Input/`
- [ ] Create user manual (based on QUICKSTART.md)
- [ ] Add application icon
- [ ] Sign executable (optional, for trusted deployment)
- [ ] Create installer for easier distribution

## Future Enhancements

**Phase 2 - Visualization** (Next):
- Connect results browser to plots
- Implement time-history plotting
- Add envelope plot by story
- Interactive plot controls (zoom, pan, cursors)
- Export plots to PNG/PDF

**Phase 3 - More Result Types**:
- Joint displacements and reactions
- Element forces (columns, beams, piers)
- Plastic hinges and nonlinear behavior
- Custom result types

**Phase 4 - Advanced Features**:
- Multi-project comparison
- Statistical analysis tools
- Custom report generation
- Batch import multiple files
- Filter and search functionality

**Phase 5 - 3D Visualization**:
- Load building geometry
- Overlay results on 3D model
- Interactive 3D navigation
- Animation over time

## Troubleshooting

### Database Issues

**"No such table" error**:
```bash
pipenv run alembic upgrade head
```

**"Database is locked"**:
- Close all app instances
- Delete `data/*.db-journal` files
- On WSL: Don't share database between WSL and Windows

### Import Issues

**Excel file not recognized**:
- Check sheet names match expected (case-sensitive)
- Verify ETABS/SAP2000 export format
- Check column headers in first row

**Import fails silently**:
- Check console output for errors
- Verify database migrations are applied
- Test with sample files from `Typical Input/`

### Theme Issues

**Light title bar on Windows**:
- Requires Windows 10 (build 19041+) or Windows 11
- Enable Windows dark mode in Settings
- See `WINDOWS_DARK_MODE.md`

**Light title bar on WSL**:
- This is expected - X11 limitation
- Test on actual Windows to see dark title bar

### Performance Issues

**Slow plotting**:
- Check data volume (PyQtGraph handles 100k+ points)
- Use downsampling for very large datasets
- Ensure PyQtGraph is using OpenGL

**Slow import**:
- Use bulk insert methods (already implemented)
- Check database indexes
- Profile with `cProfile` if needed

## Resources

**Documentation Files**:
- `QUICKSTART.md` - How to run and use
- `SETUP_COMPLETE.md` - Setup details and architecture
- `MODERN_THEME_APPLIED.md` - Theme documentation
- `WINDOWS_DARK_MODE.md` - Windows title bar details
- `DARK_TITLE_BAR_FIX.md` - Title bar fix summary
- `test_gmp_styling.py` - GMP component styling demo

**External Documentation**:
- PyQt6: https://www.riverbankcomputing.com/static/Docs/PyQt6/
- PyQtGraph: https://pyqtgraph.readthedocs.io/
- SQLAlchemy: https://docs.sqlalchemy.org/
- Alembic: https://alembic.sqlalchemy.org/

## Contact & Support

For issues or questions about this codebase, refer to:
- Legacy scripts in `Old_scripts/` for original processing logic
- Test files in `tests/` for usage examples
- Documentation files listed above

---

**Last Updated**: Current session (GMP-exact design system implemented, Windows deployment ready)
**Status**: Complete skeleton with modern UI - Ready for visualization feature development
