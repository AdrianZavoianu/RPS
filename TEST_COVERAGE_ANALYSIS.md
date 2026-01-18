# Test Coverage Analysis & Improvement Plan

**Date**: January 2025
**Current Status**: 325 passing, 1 failing, 2 skipped (~98.5% pass rate)

---

## Executive Summary

| Metric | Value |
|--------|-------|
| Source Files | 168 files |
| Lines of Code | ~43,700 |
| Test Files | 70 files |
| Total Tests | 326 |
| Test Ratio | ~0.4 tests per source file |
| Estimated Line Coverage | ~40-50% (based on module analysis) |

---

## Coverage Analysis by Module

### 1. Processing Layer (45 source files → 8 test files)
**Coverage: ~18% by file count**

| Status | Module | Lines | Priority |
|--------|--------|-------|----------|
| ✅ Good | `pushover_base_parser.py` | 200 | - |
| ✅ Good | `pushover_base_importer.py` | 300 | - |
| ✅ Good | `pushover_parser.py` | 250 | - |
| ✅ Good | `pushover_importer.py` | 200 | - |
| ✅ Good | `result_transformers.py` | 400 | - |
| ⚠️ Partial | `pushover_soil_pressure_parser.py` | 150 | Medium |
| ❌ Missing | `time_history_parser.py` | 336 | **HIGH** |
| ❌ Missing | `time_history_importer.py` | 255 | **HIGH** |
| ❌ Missing | `pushover_wall_parser.py` | 200 | Medium |
| ❌ Missing | `pushover_wall_importer.py` | 180 | Medium |
| ❌ Missing | `pushover_column_parser.py` | 200 | Medium |
| ❌ Missing | `pushover_column_importer.py` | 180 | Medium |
| ❌ Missing | `pushover_beam_parser.py` | 200 | Medium |
| ❌ Missing | `pushover_beam_importer.py` | 180 | Medium |
| ❌ Missing | `pushover_joint_parser.py` | 150 | Medium |
| ❌ Missing | `pushover_joint_importer.py` | 150 | Medium |
| ❌ Missing | `enhanced_folder_importer.py` | 400 | High |
| ❌ Missing | `folder_importer.py` | 300 | High |

### 2. GUI Layer (34 source files → 4 test files)
**Coverage: ~12% by file count**

| Status | Module | Lines | Priority |
|--------|--------|-------|----------|
| ✅ Good | `tree_browser/` (package) | 2000 | - |
| ✅ Good | `project_detail/` (package) | 2000 | - |
| ✅ Good | `export/` (package) | 1500 | - |
| ⚠️ Partial | `view_loaders_comparison` | 500 | Medium |
| ❌ Missing | `time_history_import_dialog.py` | 861 | **HIGH** |
| ❌ Missing | `result_views/time_series_animated_view.py` | 539 | **HIGH** |
| ❌ Missing | `result_views/comparison_view.py` | 523 | High |
| ❌ Missing | `result_views/pushover_curve_view.py` | 352 | Medium |
| ❌ Missing | `result_views/standard_view.py` | 104 | Low |
| ❌ Missing | `folder_import_dialog.py` | 1100 | High |
| ❌ Missing | `comparison_set_dialog.py` | 400 | Medium |
| ❌ Missing | `pushover_import_dialog.py` | 500 | Medium |
| ❌ Missing | `pushover_global_import_dialog.py` | 600 | Medium |

### 3. Services Layer (15 source files → 5 test files)
**Coverage: ~33% by file count**

| Status | Module | Lines | Priority |
|--------|--------|-------|----------|
| ✅ Good | `export_discovery.py` | 471 | - |
| ✅ Good | `pushover_context.py` | 200 | - |
| ⚠️ Partial | `export_service.py` | 954 | **HIGH** |
| ❌ Missing | `export_import_data.py` | 375 | High |
| ❌ Missing | `export_excel_sections.py` | 95 | Medium |
| ❌ Missing | `export_writer.py` | 26 | Low |
| ❌ Missing | `project_service.py` | 300 | High |
| ❌ Missing | `import_service.py` | 200 | Medium |

### 4. Database Layer (10 source files → 3 test files)
**Coverage: ~30% by file count**

| Status | Module | Lines | Priority |
|--------|--------|-------|----------|
| ✅ Good | `repositories/` (package) | 1000 | - |
| ✅ Good | `base_repository.py` | 130 | - |
| ⚠️ Partial | `element_result_repository.py` | 200 | Medium |
| ❌ Missing | `models.py` | 800 | Medium |
| ❌ Missing | `session.py` | 50 | Low |

### 5. Utils Layer (9 source files → 2 test files)
**Coverage: ~22% by file count**

| Status | Module | Lines | Priority |
|--------|--------|-------|----------|
| ✅ Good | `pushover_utils.py` | 100 | - |
| ✅ Good | `timing.py` | 50 | - |
| ❌ Missing | `color_utils.py` | 150 | Low |
| ❌ Missing | `plot_builder.py` | 200 | Medium |
| ❌ Missing | `data_utils.py` | 150 | Low |

---

## Gap Analysis

### Critical Gaps (HIGH Priority - Blocks Quality Releases)

1. **Time-Series Feature (NEW in v2.20)** - 0% coverage
   - `time_history_parser.py` (336 lines) - Parser logic untested
   - `time_history_importer.py` (255 lines) - Import logic untested
   - `time_history_import_dialog.py` (861 lines) - Dialog untested
   - `time_series_animated_view.py` (539 lines) - Animation untested
   - **Total: ~2,000 lines of completely untested code**

2. **Export System** - ~30% coverage
   - `export_service.py` (954 lines) - Core export logic partially tested
   - `export_import_data.py` (375 lines) - Re-import feature untested
   - Missing edge case tests for multi-result-set exports

3. **Folder Import System** - ~20% coverage
   - `folder_import_dialog.py` (1100 lines) - UI logic untested
   - `enhanced_folder_importer.py` (400 lines) - Core logic untested

### Medium Priority Gaps

4. **Pushover Element Parsers/Importers** - 0% coverage each
   - Wall, Column, Beam, Joint parsers (~800 lines total)
   - Wall, Column, Beam, Joint importers (~700 lines total)
   - These follow similar patterns to `pushover_base_*` (which ARE tested)

5. **Result Views** - 0% coverage
   - `comparison_view.py` (523 lines)
   - `pushover_curve_view.py` (352 lines)
   - `standard_view.py` (104 lines)

6. **Project/Import Services** - 0% coverage
   - `project_service.py` (300 lines)
   - `import_service.py` (200 lines)

### Low Priority Gaps

7. **Utility modules** - Various
   - `color_utils.py`, `data_utils.py` (300 lines total)
   - Simple helper functions, low risk

---

## Current Test Infrastructure Assessment

### Strengths
- ✅ pytest with good fixtures pattern
- ✅ Tests organized by module (database/, gui/, processing/, services/)
- ✅ Good use of mocking for database tests
- ✅ Parametrized tests for configuration validation
- ✅ E2E golden file tests for exports

### Weaknesses
- ❌ No shared fixtures in conftest.py (only path setup)
- ❌ No Qt/PyQt test fixtures for GUI testing
- ❌ No integration test database fixture
- ❌ No coverage reporting configured
- ❌ No test data fixtures (Excel files for parser tests)

---

## Improvement Plan

### Phase 1: Infrastructure (1-2 days)
**Goal: Enable efficient test development**

1. **Add pytest-cov for coverage reporting**
   ```bash
   pipenv install pytest-cov --dev
   ```
   Add to pytest.ini or pyproject.toml:
   ```ini
   [tool:pytest]
   addopts = --cov=src --cov-report=html --cov-report=term-missing
   ```

2. **Create shared fixtures in conftest.py**
   ```python
   # tests/conftest.py
   import pytest
   from sqlalchemy import create_engine
   from sqlalchemy.orm import sessionmaker

   @pytest.fixture
   def in_memory_session():
       """Create in-memory SQLite session for tests."""
       engine = create_engine("sqlite:///:memory:")
       Base.metadata.create_all(engine)
       Session = sessionmaker(bind=engine)
       session = Session()
       yield session
       session.close()

   @pytest.fixture
   def sample_project(in_memory_session):
       """Create sample project with stories and load cases."""
       ...
   ```

3. **Create test data fixtures**
   - Add `tests/fixtures/` directory
   - Create minimal Excel files for parser tests
   - Use `openpyxl` to generate programmatically

### Phase 2: Critical Coverage (3-5 days)
**Goal: Cover new Time-Series feature and critical paths**

1. **Time History Parser Tests** (`tests/processing/test_time_history_parser.py`)
   - Test `parse()` method with mock Excel data
   - Test `_detect_load_case_name()`
   - Test `_parse_story_drifts()`, `_parse_story_forces()`, etc.
   - Test `_extract_time_series_by_direction()`
   - Test `prescan_time_history_file()`
   - **Estimated: 15-20 tests**

2. **Time History Importer Tests** (`tests/processing/test_time_history_importer.py`)
   - Test `import_file()` with mock parser results
   - Test `_ensure_stories()` story creation
   - Test `_import_series()` for each result type
   - Test conflict resolution (duplicate handling)
   - **Estimated: 12-15 tests**

3. **Export Service Integration Tests** (`tests/services/test_export_service_integration.py`)
   - Test multi-result-set export
   - Test NLTHA vs Pushover context filtering
   - Test curve export for Pushover
   - **Estimated: 10-12 tests**

### Phase 3: Import System Coverage (2-3 days)
**Goal: Cover folder import and conflict resolution**

1. **Folder Import Dialog Tests** (`tests/gui/test_folder_import_dialog.py`)
   - Test prescan worker signals
   - Test load case checkbox population
   - Test conflict detection logic
   - Test import button enablement logic
   - **Estimated: 10-12 tests**

2. **Enhanced Folder Importer Tests** (`tests/processing/test_enhanced_folder_importer.py`)
   - Test conflict resolution application
   - Test selective load case import
   - Test progress callback behavior
   - **Estimated: 8-10 tests**

### Phase 4: Pushover Element Coverage (2-3 days)
**Goal: Cover pushover element parsers/importers**

Since these follow the tested `pushover_base_*` patterns, tests can be templated:

1. **Create base test template**
   ```python
   # tests/processing/base_pushover_element_test.py
   class BasePushoverElementParserTest:
       """Template for pushover element parser tests."""
       parser_class = None
       expected_sheet = None
       ...
   ```

2. **Implement per-element tests**
   - `test_pushover_wall_parser.py`
   - `test_pushover_column_parser.py`
   - `test_pushover_beam_parser.py`
   - **Estimated: 6-8 tests each**

### Phase 5: Result Views Coverage (2-3 days)
**Goal: Cover visualization widgets**

1. **Add PyQt test fixtures**
   ```python
   # tests/conftest.py
   import pytest
   from PyQt6.QtWidgets import QApplication

   @pytest.fixture(scope="session")
   def qapp():
       app = QApplication.instance() or QApplication([])
       yield app
   ```

2. **Standard View Tests** (`tests/gui/test_standard_view.py`)
   - Test data loading
   - Test plot rendering (smoke tests)
   - **Estimated: 5-6 tests**

3. **Comparison View Tests** (`tests/gui/test_comparison_view.py`)
   - Test multi-series data handling
   - Test legend generation
   - **Estimated: 5-6 tests**

4. **Time Series View Tests** (`tests/gui/test_time_series_view.py`)
   - Test animation timer logic
   - Test envelope calculation
   - Test base acceleration plot
   - **Estimated: 8-10 tests**

---

## Prioritized Action Items

### Immediate (This Sprint)
- [ ] Add pytest-cov and enable coverage reporting
- [ ] Create shared database fixtures in conftest.py
- [ ] Write tests for `time_history_parser.py`
- [ ] Write tests for `time_history_importer.py`

### Short-term (Next Sprint)
- [ ] Write tests for export service integration
- [ ] Write tests for folder import dialog
- [ ] Create test Excel fixtures

### Medium-term (Following Sprint)
- [ ] Cover pushover element parsers/importers
- [ ] Cover result views with PyQt fixtures
- [ ] Achieve 70% line coverage target

### Long-term (Quarterly)
- [ ] Achieve 80% line coverage
- [ ] Add integration tests with real Excel files
- [ ] Add performance regression tests

---

## Coverage Targets

| Milestone | Target | Timeline |
|-----------|--------|----------|
| Baseline | ~45% | Current |
| Phase 1-2 | 55% | +1 week |
| Phase 3-4 | 65% | +2 weeks |
| Phase 5 | 75% | +3 weeks |
| Maintenance | 80% | Ongoing |

---

## Appendix: Quick Wins (Low Effort, High Value)

These tests can be added quickly with existing patterns:

1. **Test prescan_time_history_file()** - 3-4 tests, uses existing parser pattern
2. **Test TimeSeriesRepository methods** - 5-6 tests, follows existing repo pattern
3. **Test export_utils.py functions** - Already has 6 tests, add 3-4 more edge cases
4. **Test color_utils.py gradient functions** - 4-5 simple unit tests

---

*Generated by Test Coverage Analysis Tool*
