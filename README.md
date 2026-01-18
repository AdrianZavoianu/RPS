# Results Processing System (RPS)

A modern desktop application for processing and visualizing structural engineering results from ETABS/SAP2000 Excel exports. Built with PyQt6, featuring a dark web-style theme, database storage, and high-performance visualization.

## Quick Start

```bash
# Install dependencies
pipenv install --dev

# Run database migrations
pipenv run alembic upgrade head

# Run the application
pipenv run python src/main.py

# Or use hot-reload for development
pipenv run python dev_watch.py
```

### Repo hygiene

- Detect stray top-level folders (e.g., accidental extracted paths): `pipenv run python scripts/check_repo_hygiene.py`

## Features

✅ **Complete Data Pipeline** – Import, process, and store envelopes, element, and foundation results
✅ **Folder-Based Import** – Batch process Excel files with prescan, conflict resolution, and consolidated stats
✅ **Structured Logging & Diagnostics** – JSON logs under `data/logs/` plus an in-app Diagnostics dialog for quick tailing
✅ **Interactive Visualization** – PyQtGraph building profile plots with comparison sets, scatter plots, and max/min views
✅ **Modern UI** – GMP-inspired design system with dark theme, responsive layout, and hot reload tooling
✅ **Configuration-Driven Extensibility** – Result types, transformers, and import tasks are declared in config/processing modules

## Logs & Diagnostics

- All runtime logs are written to `data/logs/rps.log` (JSON lines). Customize the location by calling `setup_logging(log_file=...)` before launching the UI.
- Use the status bar “Diagnostics” button to open the log viewer dialog (tail, copy path, open folder) without leaving the app.
- Importers emit `import.start`, `import.phase`, and `import.complete` events, making it easy to correlate folder imports with the UI progress log.

## Documentation

This project has comprehensive documentation organized into three main files:

- **[PRD.md](PRD.md)** - Product requirements, features, workflows, and roadmap
- **[ARCHITECTURE.md](ARCHITECTURE.md)** - Technical architecture, data model, and design patterns
- **[CLAUDE.md](CLAUDE.md)** - Development guide for working with Claude Code

## Technology Stack

- **UI Framework**: PyQt6
- **Visualization**: PyQtGraph (high-performance plotting)
- **Database**: SQLite with SQLAlchemy ORM + Alembic migrations
- **Data Processing**: Pandas, NumPy
- **Package Management**: Pipenv

## Project Status

**Production-ready** with core visualization features fully implemented:
- ✅ Project management with card-based UI
- ✅ Single file and folder batch import
- ✅ Story drifts, accelerations, and forces visualization
- ✅ Building profile plots with interactive selection
- ✅ Configuration-driven architecture for easy extension
- ✅ Hybrid normalized + cache data model for performance

**Next Steps**: polish regression tests/UI docs, add analytics/alerting views, and explore time-series visualization + external integrations.

## Testing

```bash
pipenv run pytest
```

New tests cover the import task registry, folder import aggregators, project runtime/controller wiring, and logging utilities. Additions should keep parity by extending the relevant suites under `tests/`.

## Developer checklist

- `pipenv run black src tests`
- `pipenv run flake8`
- `pipenv run pytest`
- `pipenv run python scripts/check_repo_hygiene.py`

## Platform Support

- **Primary**: Windows 10/11
- **Development**: Windows, WSL2, Linux
- **Deployment**: Standalone .exe via PyInstaller

## License

Internal project for structural engineering team.
