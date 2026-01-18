# Refactoring Plan

Grounded in the current assessment: large monolithic modules (import/export/UI), duplicated parsing logic, mixed concerns across services/repositories, stray artifacts, and uneven test coverage. Goal: improve modularity, correctness, and maintainability without slowing delivery.

## Objectives
- Reduce file size and complexity in import/export/UI flows; isolate concerns (I/O, parsing, persistence, presentation).
- Standardize repository/session usage and structured logging.
- Clean the repo tree and keep tooling guardrails tight.
- Raise automated coverage for touched areas, especially import/export and controller wiring.

## Guiding Principles
- Small, vertical slices per PR; keep behavior stable and add regression tests first.
- Reuse shared utilities/config (result metadata, logging, sheet discovery) rather than duplicating.
- UI widgets stay dumb; controllers handle data orchestration.
- Favor typed DTOs/TypedDicts/dataclasses at module boundaries.

## Workstreams and Steps

### 1) Repository Hygiene
- Delete or archive stray build artifacts (`C?SoftDevRPSsrcdatabaserepositories/`, `C?SoftDevRPSsrcguiexport/`); add a lightweight sanity check script/CI step that fails on unexpected top-level dirs.
- Move ad-hoc `Old_scripts/` tests/diagnostics into `tests/fixtures` or docs; keep only live fixtures under `tests/resources`.

### 2) Architecture & Boundaries
- Document the layered flow (UI → services → repositories → DB) in `ARCHITECTURE.md` addendum and enforce through imports (no DB access from widgets).
- Centralize session creation/cleanup in a single helper and pass repositories as dependencies into services/controllers.
- Add typed interfaces for services used by controllers to decouple UI from concrete implementations.

### 3) Import Pipeline Split
- Break `processing/data_importer.py` into modules: `metadata_import`, `element_import`, `foundation_import`, `cache_builder`, `timing/logging`.
- Extract common parsing/validation helpers (sheet presence, naming normalization) shared by NLTHA and pushover importers.
- Align pushover importers to a base task/config pattern; remove duplicated direction/load-case mapping logic.
- Tests: add regression cases for metadata import, element/foundation import, and cache generation using existing Excel samples.
Status: Orchestration and logging split into `import_runner` and `import_logging`; DataImporter and folder importers now share structured logging and task execution. Added regression tests for element/foundation import + cache generation and import runner. Next: pull shared parsing/validation helpers out of importers and add fixture-backed regression.

### 4) Export Pipeline Split
- Decompose `services/export_service.py` into discovery/query, formatting, and writers (Excel/CSV). Reuse `config/result_config.py` metadata for result type definitions.
- Move exporter utilities (worksheet naming, dataframes to Excel) into shared helpers.
- Tests: golden-file comparisons for NLTHA and pushover contexts; verify context-aware filtering and curve export selection.
- Status: helpers extracted (`export_utils`, `export_writer`, `export_metadata`, `export_discovery`, `export_excel_sections`, `export_import_data`, `export_formatting`, `export_pushover`). Next: add end-to-end export regression using a small fixture DB and cover context-aware filtering.

### 5) UI Modularization
- Refactor oversized widgets/dialogs (`gui/maxmin_drifts_widget.py`, `gui/pushover_global_import_dialog.py`, `gui/folder_import_dialog.py`, `gui/project_detail/window.py`, `gui/export/dialogs.py`) into smaller panes/components.
- Push data loading to controllers (`gui/controllers/*`); keep widgets focused on rendering and signals.
- Consolidate styling/layout constants in `gui/styles.py` and small reusable components under `gui/components/`.
- Tests: controller/unit tests for table builders and dialog wiring; minimal Qt smoke tests where feasible.
- Status: not started; next step is to split `gui/project_detail/window.py` into controller + view submodules and add controller tests.
Status: ProjectDetail modularized (content area, loaders/handlers). Remaining dialogs/widgets still need splitting and controller-centric wiring/tests.

### 6) Database Layer Cleanup
- Introduce repository mixins for common queries/cache access; reduce duplication across `src/database/repositories`.
- Tighten `database/models.py` with typed relationships and inline field docs; ensure Alembic migrations stay in sync.
- Add integration tests for key repositories using the temp DB fixture.

### 7) Observability & Performance
- Turn `PhaseTimer` into a shared utility; ensure structured logging across import/export services.
- Audit cache build paths for heavy queries; add basic metrics (durations, row counts) to logs.
- Verify worker-thread usage for long-running tasks and consistent progress callbacks.

### 8) Testing & Tooling
- Extend pytest suites to mirror new module splits; add `tests/resources` golden data for import/export.
- Add pre-commit/CI hooks for `black`, `flake8`, and optional `mypy` on services/processing.
- Provide a developer checklist in `README` for running format/lint/tests before PRs.

## Sequencing (suggested)
1. Repo hygiene and architecture guardrails (session helper, docs update, stray dirs cleanup).
2. Import pipeline split + tests (highest risk/complexity, foundational for data correctness).
3. Export pipeline split + tests (reuses import/query shapes).
4. UI modularization and controller strengthening (incremental per widget/dialog).
5. Database repository consolidation and Alembic alignment.
6. Observability polish and tooling tightening.

## Definition of Done (per workstream)
- Complexity reduction: targeted files under ~400–500 lines with clear boundaries.
- Tests: added/updated pytest modules covering new slices; green `pipenv run pytest`.
- Style/tooling: `pipenv run black src tests` and `pipenv run flake8` clean.
- Docs: `ARCHITECTURE.md`/`README.md` notes for new patterns; TODOs captured for follow-ups if deferred.
