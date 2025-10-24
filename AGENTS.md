# Repository Guidelines

## Project Structure & Module Organization
- `src/` holds the application code: `gui/` for PyQt6 windows and widgets, `processing/` for ETABS/SAP2000 parsers, `database/` for SQLAlchemy models and session utilities, `config/` for runtime settings, and `utils/` for shared helpers. Entry point: `src/main.py`.
- `alembic/` and `alembic.ini` track database migrations; run them before using new features.
- `tests/` mirrors core modules with pytest suites and shared fixtures in `tests/conftest.py`.
- `data/` is a scratch area for local exports, `resources/` stores bundled assets, and `Typical Input/` contains reference Excel folders.

## Build, Test, and Development Commands
- `pipenv install --dev` — install application and development dependencies.
- `pipenv run alembic upgrade head` — apply the latest schema to the SQLite database.
- `pipenv run python src/main.py` — launch the desktop client.
- `pipenv run python dev_watch.py` — enable hot-reload when iterating on UI code.
- `pipenv run pytest` — execute all automated tests.
- `pipenv run black src tests` and `pipenv run flake8` — format and lint before pushing.

## Coding Style & Naming Conventions
- Target Python 3.11+, four-space indentation, Black formatting, and Flake8 cleanliness; keep imports sorted to Black’s profile.
- Use `snake_case` for modules/functions, `PascalCase` for classes, and suffix Qt components with `_widget.py` or `_window.py` (e.g., `results_table_widget.py`).
- Add type hints for new APIs; prefer dataclasses or TypedDicts when moving structured data across layers.
- Centralize reusable UI styling in `gui/styles.py` rather than scattering constants.

## Testing Guidelines
- Name test modules `test_<feature>.py` and keep them aligned with the feature under test (see `tests/test_cache.py` mirroring `processing/cache` logic).
- Reuse fixtures from `tests/conftest.py` for temporary SQLite databases; place new shared fixtures there.
- For parsers or plotting logic, add regression samples under `Typical Input/` or `resources/` and assert dataframe shape and key metrics.
- Aim for coverage parity with touched modules and include at least one failure-mode test for new ETABS data transforms.

## Commit & Pull Request Guidelines
- Keep commits short and imperative, mirroring history such as “Data model and style updated”; add scoped prefixes (`gui:`, `db:`) when it clarifies impact.
- Squash WIP commits before PRs; in the PR body note motivation, major changes, migrations, and test evidence.
- Link related PRD tasks or issues, and attach before/after screenshots or GIFs for UI work.
- Call out data migration risks explicitly and capture follow-up tasks with TODOs or tracking issues.
