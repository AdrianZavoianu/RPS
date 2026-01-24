# Remaining Refactoring Tasks

This document tracks the remaining items from the comprehensive refactoring plan. The completed phases include:

- ✅ Phase 1: Immediate Cleanup (V1 importers deleted, signal bug fixed)
- ✅ Phase 2.1: PyQtGraph Plot Factory
- ✅ Phase 2.2: Design Token Standardization
- ✅ Phase 3.1: BasePushoverJointImporter base class
- ✅ Phase 3.2: Decompose Large GUI Files
- ✅ Phase 3.3: Dialog Reorganization (gui/dialogs/ package)
- ✅ Phase 4: Comprehensive Test Coverage
- ✅ Phase 5.1: Relocate result_service to services/
- ✅ Phase 5.2: Standardize data_access.py Usage
- ✅ Phase 5.3: Consolidate Folder Importers
- ✅ Phase 5.4: Decompose export_service.py
- ✅ Phase 6.1: Delete Old_scripts directory
- ✅ Phase 6.2: Clean up empty root gui/ folder
- ✅ Phase 6.3: Manage Large Sample Data (Git LFS)
- ✅ Phase 6.4: Performance instrumentation (@timed decorator)
- ✅ Phase 6.5: Review excel_cache.py

---

## ✅ Phase 3.2: Decompose Large GUI Files (Completed)

**Priority:** Medium
**Estimated Effort:** 8 hours

### Files to Decompose

#### 1. `src/gui/reporting/report_preview_widget.py` (1,536 lines)
Extract rendering logic into focused modules:
- `ReportPageBuilder` - Page layout and section positioning
- `ReportTableRenderer` - Table drawing logic
- `ReportPlotRenderer` - Building profile plot rendering
- `ReportHeaderFooter` - Header/footer rendering

#### 2. `src/gui/maxmin_drifts_widget.py` (1,422 lines)
Extract into builders:
- `MaxMinPlotBuilder` - Plot construction and styling
- `MaxMinTableBuilder` - Table data preparation and formatting
- `MaxMinDataProcessor` - Data transformation logic

### Approach
1. Identify cohesive blocks of functionality
2. Extract into classes with single responsibilities
3. Keep widget as thin orchestrator
4. Maintain backward compatibility with existing API

---

## ✅ Phase 4: Comprehensive Test Coverage (Completed)

**Priority:** Medium
**Estimated Effort:** 16 hours

### New Test Files to Create

#### 1. `tests/gui/test_import_dialogs.py`
Test coverage for import dialog functionality:
- `test_folder_import_dialog_setup_ui()` - UI initialization
- `test_folder_import_dialog_prescan()` - File scanning behavior
- `test_worker_signal_emission_format()` - Signal signature consistency
- `test_progress_updates_reach_ui()` - Progress bar updates
- `test_import_dialog_base_inheritance()` - Base class pattern
- `test_pushover_import_dialog_validation()` - Input validation
- `test_time_history_import_dialog_load_cases()` - Load case selection

#### 2. `tests/gui/test_widgets.py`
Widget behavior tests:
- `test_results_table_widget_load_data()` - Data loading
- `test_results_plot_widget_scaling()` - Plot scaling behavior
- `test_maxmin_drifts_widget_data_binding()` - Data binding
- `test_all_rotations_widget_histogram()` - Histogram rendering
- `test_beam_rotations_widget_tabs()` - Tab switching

#### 3. `tests/gui/test_signal_patterns.py`
Signal consistency tests:
- `test_all_workers_have_consistent_signal_signatures()` - Pattern enforcement
- `test_progress_signal_params_are_str_int_int()` - Standard signature
- `test_finished_signal_emits_on_completion()` - Completion signaling
- `test_error_signal_includes_message()` - Error message propagation

#### 4. `tests/gui/conftest.py`
Shared test fixtures:
- `@pytest.fixture` for QApplication instance
- Mock factories for dialogs and workers
- Common test data generators

### Expand Existing Tests

#### `tests/gui/test_export_dialog.py` (78 → 200+ lines)
- `test_comprehensive_export_worker_runs()`
- `test_export_format_selection()`
- `test_result_set_filtering_by_context()`

#### `tests/gui/test_project_detail.py` (72 → 150+ lines)
- `test_event_handler_selection_changed()`
- `test_view_loader_caching()`
- `test_context_switching()`

---

## ✅ Phase 5.2: Standardize data_access.py Usage (Completed)

**Priority:** Low
**Estimated Effort:** 4 hours

### Problem
`src/services/data_access.py` exists as a facade but isn't consistently used. Direct repository imports are scattered throughout GUI and processing code.

### Tasks
1. Audit all direct `Repository` imports in `gui/` and `processing/`
2. Identify candidates for data_access facade pattern
3. Add missing facade methods to `data_access.py`
4. Migrate high-frequency access patterns first
5. Document the facade API

### Benefits
- Consistent data access patterns
- Easier testing with mock injection
- Single point for caching strategies

---

## ✅ Phase 5.3: Consolidate Folder Importers (Completed)

**Priority:** Low
**Estimated Effort:** 4 hours

### Problem
Two folder importer implementations exist:
- `src/processing/folder_importer.py` - Basic, older implementation
- `src/processing/enhanced_folder_importer.py` - Newer with conflict resolution

### Tasks
1. Review both implementations for unique features
2. Merge all features into single `folder_importer.py`
3. Keep enhanced conflict resolution capabilities
4. Update all imports throughout codebase
5. Delete redundant file
6. Add migration tests

### Considerations
- The enhanced version has conflict resolution dialogs
- Need to preserve lazy imports for GUI classes to avoid circular deps

---

## ✅ Phase 5.4: Decompose export_service.py (Completed)

**Priority:** Low
**Estimated Effort:** 4 hours

### Problem
`src/services/export_service.py` (~800 lines) is a monolithic orchestrator handling multiple export formats and result types.

### Target Structure
```
src/services/export/
├── __init__.py           # Re-exports for backward compatibility
├── service.py            # Main ExportService orchestrator
├── excel_writer.py       # Excel formatting and sheet creation
├── csv_writer.py         # CSV file writing
└── curve_exporter.py     # Pushover curve export logic
```

### Tasks
1. Create `services/export/` package
2. Extract Excel writing logic to `excel_writer.py`
3. Extract CSV writing logic to `csv_writer.py`
4. Extract curve export to `curve_exporter.py`
5. Keep `service.py` as thin orchestrator
6. Create backward-compat re-exports at old location
7. Update imports in callers

---

## ✅ Phase 6.3: Manage Large Sample Data (Completed)

**Priority:** Low
**Estimated Effort:** 2 hours

### Problem
Large sample data folders in the repository increase clone size and slow down operations.

### Options

#### Option A: Git LFS (Recommended)
- Seamless developer experience
- Files tracked normally but stored externally
- `git lfs install && git lfs track "*.xlsx"`

#### Option B: Separate Data Repository
- Complete separation of code and data
- Requires additional clone step
- Better for very large datasets

#### Option C: .gitignore + External Storage
- Remove from repo entirely
- Document download location
- CI/CD must fetch separately

### Recommended Approach
Use Git LFS for Excel sample files:
```bash
git lfs install
git lfs track "data/samples/**/*.xlsx"
git add .gitattributes
git commit -m "Configure Git LFS for sample data"
```

---

## ✅ Phase 6.5: Review excel_cache.py (Completed)

**Priority:** Low
**Estimated Effort:** 2 hours

### Problem
`src/processing/excel_cache.py` (238 lines) is a new file that needs review for correctness and test coverage.

### Tasks
1. Review caching strategy implementation
2. Verify cache invalidation logic is correct
3. Check for memory leak potential (unbounded cache growth)
4. Add tests for cache behavior:
   - `test_cache_hit_returns_cached_value()`
   - `test_cache_miss_calls_loader()`
   - `test_cache_invalidation_clears_entry()`
   - `test_cache_respects_max_size()`
5. Document cache lifecycle and configuration
6. Consider integration with `@timed` decorator for monitoring

### Potential Issues to Check
- Thread safety if used from multiple workers
- Memory management for large Excel files
- Cache key uniqueness

---

## Summary

| Phase | Description | Priority | Effort | Status |
|-------|-------------|----------|--------|--------|
| 3.2 | Decompose large GUI files | Medium | 8h | ✅ Done |
| 4 | Test coverage expansion | Medium | 16h | ✅ Done |
| 5.2 | Standardize data_access.py | Low | 4h | ✅ Done |
| 5.3 | Consolidate folder importers | Low | 4h | ✅ Done |
| 5.4 | Decompose export_service.py | Low | 4h | ✅ Done |
| 6.3 | Git LFS for sample data | Low | 2h | ✅ Done |
| 6.5 | Review excel_cache.py | Low | 2h | ✅ Done |
| **Total** | | | **40h** | ✅ Complete |

---

*Last Updated: 2026-01-22*
