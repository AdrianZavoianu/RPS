# PRD - Results Processing System (RPS)

## Document info
- Status: production-ready
- Current release: v2.22 (2025-01-18)
- Last updated: 2026-01-24
- Owner: Structural engineering tools team (internal)

## Product summary
RPS is a desktop application for importing ETABS/SAP2000 Excel exports, persisting results to SQLite, and providing fast visualization, comparison, reporting, and export workflows for structural analysis data (NLTHA and pushover).

## Goals
- Reduce time to review key results (drifts, forces, displacements, accelerations).
- Provide consistent, repeatable processing and comparisons across multiple result sets.
- Offer responsive plots and tables for global, element, joint, and time-series results.
- Produce exportable outputs (Excel/PDF) suitable for review and deliverables.

## Non-goals
- Cloud or multi-user collaboration features.
- Direct ETABS/SAP2000 API integration.
- Full 3D model rendering or BIM viewer
- Web or mobile deployment.

## Target users
- Structural engineers reviewing NLTHA and pushover analysis outputs.
- Project leads preparing deliverables and reports.
- QA/peer reviewers validating envelopes and comparisons.

## Core user workflows
1. Create/open a project from the project grid.
2. Import results (single file or folder batch) with load case prescan and conflict resolution.
3. Browse results via the tree and inspect tables/plots by direction, element, or joint.
4. Create comparison sets across multiple result sets and review ratio analysis.
5. Generate a PDF report for NLTHA global results.
6. Export selected results (Excel/CSV) or export the full project.
7. Use diagnostics to review logs when imports or exports fail.

## Functional requirements

### Project management
- Maintain a catalog of projects with per-project SQLite databases under `data/projects/{slug}`.
- Prevent duplicate windows for the same project (single-instance per project).
- Support project delete/archive via catalog metadata.

### Import
- Support single-file import and folder batch import.
- Prescan folders to discover load cases, detect conflicts, and collect foundation joints.
- Allow conflict resolution and selective load case import.
- Import NLTHA global results, element results, and foundation/joint results.
- Import pushover curves (first) and pushover results (second) into existing result sets.
- Import time-series NLTHA data and associate with existing result sets.
- Provide progress updates and structured log events for each import phase.

### Processing and data model
- Normalize results into ORM tables and build cache tables for fast queries.
- Maintain global, element, joint, max/min, and time-series caches.
- Preserve story order and load case ordering consistently across views.
- Use configuration-driven result types and transformers for extensibility.

### Visualization
- Tree browser navigation for result sets, comparisons, and time-series.
- Standard result view: table + building profile plot for directional results.
- Max/min envelope view where applicable (e.g., drifts).
- Element views for walls/columns/beams; joint views for foundation results.
- Pushover curve view with table and plot plus load case mapping.
- Time-series animated view with playback controls and envelopes.

### Comparisons
- Create comparison sets across 2+ result sets.
- Compare global, element, and joint results with ratio columns.
- Display comparison plots with multi-series legends.

### Reporting and export
- Generate PDF reports for NLTHA global results with preview and print.
- Context-aware export dialog (NLTHA vs Pushover) with filtered result sets and types.
- Export to Excel or CSV (CSV not supported for curves), combined or per-result-set.
- Export a full project to Excel for re-import.

### Diagnostics and logging
- Write JSON logs to `data/logs/rps.log` with import lifecycle events.
- Provide an in-app Diagnostics dialog to tail logs and open log folders.

### Configuration and extensibility
- Define result types in `config/result_config.py`.
- Register transformers in `processing/result_transformers.py`.
- Provide extension points for new result types, import sources, and UI views.

## Non-functional requirements
- Desktop-only, offline operation.
- Windows 10/11 primary support; Linux/WSL2 supported for development.
- SQLite storage with per-project database files.
- Responsive UI through caching and lazy-loading of datasets.
- Safe session management with scoped transactions and error handling.
- Maintainable layered architecture (UI -> Service -> Repository -> Database).
- Automated tests via pytest for core processing and utilities.

## UX requirements
- Follow `DESIGN.md` for dark, minimal, data-first styling.
- Consistent typography, spacing, and color palette across dialogs and views.
- Subtle hover/selection states and geometric iconography (no emoji icons).
- Reuse standardized dialog layouts for import, export, and reporting flows.

## Constraints and assumptions
- ETABS/SAP2000 Excel exports are the primary and supported input format.
- Single-user concurrency model (no shared DB writes).
- Element results currently focus on pier-based elements.

## Known limitations (current)
- Single-user desktop app only (no concurrent multi-user access).
- SQLite limits for very large datasets.
- Element results limited to piers (no full 3D model coverage).
- Time-series support is global results only (no element-level time series).

## Success metrics
- Typical project folder import completes successfully with caches built.
- Engineers can locate and visualize key results within minutes.
- Exported Excel/PDF outputs are accepted for review/deliverables without rework.

## Roadmap (based on current state)

### Near-term
- Expand regression tests and UI documentation.
- Add analytics/alerting views for quicker result QA.
- Improve diagnostics and traceability for imports and exports.

### Future
- Element-level time-series visualization.
- Broader element result coverage beyond piers.
- Optional external integrations for data exchange automation.
- Evaluate multi-user or shared database workflows.

## Out of scope
- Cloud collaboration, authentication, and permissions.
- Live ETABS/SAP2000 API integrations.
- Web-based deployment or mobile support.
