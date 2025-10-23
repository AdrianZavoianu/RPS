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

## Features

✅ **Complete Data Pipeline** - Import, process, and store structural analysis results
✅ **Folder-Based Import** - Batch process multiple Excel files with progress tracking
✅ **Interactive Visualization** - PyQtGraph building profile plots with 100k+ data point support
✅ **Compact Tables** - Auto-fitting tables with color-coded gradients
✅ **Modern UI** - GMP-exact design system with dark theme
✅ **Hot-Reload Development** - Web-style auto-restart on save

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

**Next Steps**: Add more result types (joint displacements, element forces), time-series visualization, and export functionality.

## Platform Support

- **Primary**: Windows 10/11
- **Development**: Windows, WSL2, Linux
- **Deployment**: Standalone .exe via PyInstaller

## License

Internal project for structural engineering team.
