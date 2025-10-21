# Results Processing System (RPS)

A desktop application for processing and visualizing structural engineering results from ETABS/SAP2000 Excel exports.

## Features

- Import and parse multi-sheet Excel files with structural analysis results
- Store results in local SQLite database
- Interactive time-history visualization
- Statistical analysis and reporting
- Expandable for 3D building model integration

## Technology Stack

- **UI Framework**: PyQt6
- **Visualization**: PyQtGraph (high-performance plotting)
- **Database**: SQLite with SQLAlchemy ORM
- **Data Processing**: Pandas, NumPy
- **Package Management**: Pipenv

## Setup

### Prerequisites

- Python 3.11
- Pipenv

### Installation

```bash
# Clone the repository
cd /path/to/RPS

# Install dependencies
pipenv install --dev

# Activate virtual environment
pipenv shell
```

## Development

### Running the Application

```bash
pipenv run python src/main.py
```

### Running Tests

```bash
pipenv run pytest
```

### Code Formatting

```bash
pipenv run black src/
```

### Building Executable

```bash
pipenv run pyinstaller src/main.py --onefile --windowed --name RPS
```

## Project Structure

```
RPS/
├── src/                    # Application source code
│   ├── gui/               # UI components
│   ├── processing/        # Business logic
│   ├── database/          # Database models and access
│   ├── utils/             # Helper functions
│   └── main.py            # Application entry point
├── resources/             # UI files and assets
│   ├── ui/               # Qt Designer .ui files
│   └── icons/            # Application icons
├── data/                  # Local SQLite databases
├── tests/                 # Unit tests
├── Old_scripts/           # Legacy processing scripts
├── Typical Input/         # Sample Excel files
├── Pipfile               # Dependency declarations
└── Pipfile.lock          # Locked dependency versions
```

## Usage

1. Launch the application
2. Import Excel files via File > Import
3. Browse and filter results
4. Visualize time-history data
5. Export processed results

## Development Status

**Phase 1 (Current)**: Initial setup and skeleton code
- [x] Project structure
- [x] Pipenv environment
- [ ] Database models
- [ ] Basic UI framework
- [ ] Excel import functionality

**Phase 2**: Core features
- [ ] Results visualization
- [ ] Statistical processing
- [ ] Data export

**Phase 3**: Advanced features
- [ ] 3D building model integration
- [ ] Advanced analytics
- [ ] Custom reporting

## License

Internal project for structural engineering team.
