# Quick Start Guide - Results Processing System (RPS)

## Prerequisites

- Python 3.11+
- Pipenv installed

**Note**: This app is designed for Windows but can be developed on WSL/Linux. The dark title bar only works on Windows 10/11. See `WINDOWS_DARK_MODE.md` for details.

## Initial Setup

### 1. Install Dependencies

```bash
# Install all dependencies (production and development)
pipenv install --dev
```

### 2. Initialize Database

```bash
# Run database migrations to create tables
pipenv run alembic upgrade head
```

## Running the Application

### Option 1: Using Pipenv Run

```bash
pipenv run python src/main.py
```

### Option 2: Activate Virtual Environment First

```bash
# Activate the virtual environment
pipenv shell

# Run the application
python src/main.py
```

## Using the Application

### Importing Excel Data

1. Click **File → Import Excel...** (or press `Ctrl+I`)
2. Click **Browse...** to select an Excel file from `Typical Input/` folder
3. Enter a **Project Name** (e.g., "160Wil")
4. Optionally enter an **Analysis Type** (e.g., "DERG", "MCR")
5. Click **OK** to import

The application will:
- Parse the Excel file
- Extract story drifts, accelerations, and forces
- Store data in the SQLite database (`data/rps.db`)
- Display import statistics

### Browsing Results

After import, the **Results Browser** (left panel) will show:
- Projects
- Load Cases (e.g., TH01, TH02, MCR1)
- Result Types (Story Drifts, Accelerations, Forces)

### Viewing Data

- Select items in the Results Browser to view details
- Use the **Visualization** panel (right) for plots (coming soon)
- Click **View → Refresh** (or press `F5`) to reload data

## Development

### Running Tests

```bash
pipenv run pytest
```

### Code Formatting

```bash
pipenv run black src/
```

### Database Migrations

```bash
# Create a new migration after model changes
pipenv run alembic revision --autogenerate -m "Description of changes"

# Apply migrations
pipenv run alembic upgrade head

# Rollback last migration
pipenv run alembic downgrade -1
```

### Building Executable

```bash
pipenv run pyinstaller src/main.py --onefile --windowed --name RPS
```

The executable will be in the `dist/` folder.

## Project Structure

```
RPS/
├── src/
│   ├── main.py              # Application entry point
│   ├── gui/                 # UI components
│   │   ├── main_window.py
│   │   ├── import_dialog.py
│   │   ├── results_browser.py
│   │   └── visualization_widget.py
│   ├── processing/          # Data processing
│   │   ├── excel_parser.py
│   │   ├── result_processor.py
│   │   └── data_importer.py
│   └── database/            # Database layer
│       ├── base.py
│       ├── models.py
│       └── repository.py
├── data/
│   └── rps.db              # SQLite database (auto-created)
├── Typical Input/          # Sample Excel files
└── Old_scripts/            # Legacy processing scripts (reference)
```

## Database Location

The SQLite database is stored at: `data/rps.db`

To reset the database, simply delete this file and run migrations again:

```bash
rm data/rps.db
pipenv run alembic upgrade head
```

## Common Issues

### "No such table" Error

Run database migrations:
```bash
pipenv run alembic upgrade head
```

### Import Fails

- Ensure Excel file has the expected sheet names:
  - "Story Drifts"
  - "Story Accelerations"
  - "Story Forces"
- Check that column headers match ETABS/SAP2000 format
- View error details in the error dialog

### Application Won't Start

- Ensure pipenv environment is activated
- Check Python version: `python --version` (should be 3.11+)
- Reinstall dependencies: `pipenv install --dev`

### Title Bar is Light on Windows

The dark title bar requires Windows 10 (build 19041+) or Windows 11:
- Update Windows to latest version
- Enable dark mode: Settings → Personalization → Colors → Dark
- See `WINDOWS_DARK_MODE.md` for details

### Title Bar is Light on WSL

This is normal! WSL runs Linux, which doesn't support Windows title bar styling. The dark title bar only works when running natively on Windows.

## Next Steps

Now that you have the skeleton working:

1. **Test with real data**: Import one of the Excel files from `Typical Input/`
2. **Implement visualization**: Connect results browser to PyQtGraph plots
3. **Add more result types**: Extend to support beams, columns, piers, etc.
4. **Enhance UI**: Add filtering, search, export functionality
5. **Statistics**: Implement envelope calculations and comparisons

## Support

See `README.md` for full project documentation.
See `CLAUDE.md` for development guidance.
