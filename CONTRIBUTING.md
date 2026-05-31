# Contributing to Results Processing System (RPS)

Thank you for your interest in contributing to RPS! We welcome contributions from engineers, researchers, and open-source developers to help improve structural engineering results processing.

By contributing to this project, you agree that your contributions will be licensed under its **GNU General Public License v3 (GPLv3)**.

---

## 1. Development Setup

RPS is a desktop application written in Python 3.11+ using the PyQt6 toolkit, SQLite for local storage, and Pandas/PyQtGraph for analysis and plotting.

### Prerequisites
* **Python 3.11 or higher**
* **Pipenv** (for package and dependency management)
* **Git**

### Installation
1. **Clone the repository:**
   ```bash
   git clone https://github.com/AdrianZavoianu/RPS.git
   cd RPS
   ```

2. **Install application & development dependencies:**
   ```bash
   pipenv install --dev
   ```

3. **Initialize the local SQLite database & run schema migrations:**
   ```bash
   pipenv run alembic upgrade head
   ```

4. **Launch the desktop application:**
   ```bash
   pipenv run python src/main.py
   ```

5. **Enable hot-reload for GUI iteration:**
   If you are modifying UI components under `src/gui/`, you can use our dev watcher to automatically reload changes:
   ```bash
   pipenv run python dev_watch.py
   ```

---

## 2. Code Quality & Coding Style

We maintain high standards of code hygiene to ensure maintainability, readability, and security.

### Style Guidelines
* **Code Formatting:** We use **Black** for deterministic code formatting. Keep lines to a maximum of 100 characters.
* **Imports:** Keep imports clean and sorted according to Black's profile using **isort**.
* **Linting:** Code must be free of lint errors reported by **Flake8**.
* **Type Hints:** Add clear type hints for all new APIs and functions to facilitate IDE autocomplete and static type safety. Prefer dataclasses or TypedDicts when moving structured data across layers.
* **Naming Conventions:**
  * Use `snake_case` for modules, packages, and functions.
  * Use `PascalCase` class names.
  * Suffix Qt UI components with `_widget.py` or `_window.py` (e.g., `results_table_widget.py`).

### Verification Commands
Before submitting your changes, verify that your code adheres to our code quality standards:
```bash
# Auto-format code
pipenv run black src tests
pipenv run isort src tests

# Check linting
pipenv run flake8

# Run type checker (optional but recommended)
pipenv run mypy src
```

---

## 3. Testing Guidelines

Automated testing is crucial to prevent regressions, especially when working with engineering datasets where accuracy is critical.

* **Test Suite:** We use **pytest** for unit and integration testing.
* **File Naming:** Test modules must be named `test_<feature>.py` and reside under a directory mirroring `src/` (e.g., tests mirroring `src/processing/cache` should be placed under `tests/processing/test_cache.py`).
* **Shared Fixtures:** Re-use fixtures defined in `tests/conftest.py` for temporary SQLite database sessions rather than instantiating raw DB connections.
* **Coverage:** Keep test coverage at parity with the touched modules. For parser updates or new data transforms, add regression Excel samples under `test_input/` or `resources/` and assert dataframe shape and metric validity.
* **Executing Tests:**
   ```bash
   pipenv run pytest
   ```

---

## 4. Repository Hygiene

To ensure clean builds and avoid cluttering the codebase:
1. Do not commit temporary directories, extracted build paths, or virtual environments.
2. Run our repository hygiene checker before committing:
   ```bash
   pipenv run python scripts/check_repo_hygiene.py
   ```
3. Avoid raw string interpolation in SQL queries. Always use the SQLAlchemy ORM or parameterized bindings to protect against SQL injections.

---

## 5. Pull Request & Commit Guidelines

When you are ready to submit your contribution, please follow these steps:

### Commit Messages
* Keep commits short, imperative, and descriptive (e.g., `db: Add index to cache tables`, `gui: Implement WCAG keyboard focus for tree browser`).
* Use scoped prefixes (such as `gui:`, `db:`, `processing:`, `docs:`) to make the git log easy to parse.
* Squash work-in-progress (WIP) commits before requesting review.

### Pull Request Checklist
1. Provide a clear description of the motivation behind the change, what was modified, and how it was tested.
2. Call out database schema migrations explicitly, detailing any potential migration risks.
3. Attach before/after screenshots or GIFs if you updated or introduced new UI components.
4. Reference any relevant requirements/roadmap items from `PRD.md` or issues.

---

*Thank you for contributing to the open-source digital commons! Together we are building trustable, accessible, and high-quality software for engineers worldwide.*
