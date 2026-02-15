# RPS Architecture

**Version**: 2.22 | **Date**: 2026-01-25

> Full implementation details in code comments and docstrings. This doc covers key patterns only.

---

## 1. System Overview

**RPS** = Results Processing System for structural engineering (ETABS/SAP2000)

**Stack**: PyQt6 (UI) + PyQtGraph (plots) + SQLite (data) + SQLAlchemy (ORM) + Pandas (processing)

**Architecture**: Layered (UI → Service → Repository → Database)

### Layering Rules
- UI/widgets do not talk directly to repositories; services own data access
- Sessions via `database.session.project_session_factory` / `catalog_session_factory`
- Controller dependencies typed in `gui.controllers.types`
- Export pipeline lives in `services/export/`; legacy `services/export_*` shims remain for compatibility

### Session Management
- **GUI queries**: Route through `DataAccessService` with short-lived sessions via `_session_scope()`
- **Worker threads**: Create `DataAccessService(session_factory)` in worker, not main thread
- **Import dialogs**: Pass `session_factory` (callable), not session instance
- **Long-lived sessions**: `ProjectDetailWindow` uses one for UI responsiveness; call `session.expire_all()` after imports

---

## 2. Data Model (27 Tables)

### Catalog Database (`data/catalog.db`)
- `catalog_projects` - Project metadata + DB paths

### Per-Project Database (`data/projects/{slug}/{slug}.db`)

| Category | Tables |
|----------|--------|
| **Core** | projects, stories, load_cases |
| **Result Sets** | result_sets, comparison_sets, result_categories |
| **Elements** | elements |
| **Global Results** | story_drifts, story_accelerations, story_forces, story_displacements |
| **Element Results** | wall_shears, quad_rotations, column_shears, column_axials, column_rotations, beam_rotations |
| **Joint Results** | soil_pressures, vertical_displacements |
| **Pushover** | pushover_cases, pushover_curve_points |
| **Cache** | global_results_cache, element_results_cache, joint_results_cache, absolute_maxmin_drifts, time_series_global_cache |
| **Time History** | time_history_data |

### Key Model Notes

**ComparisonSet**: Stores comparison configuration
- `result_set_ids` - JSON array of result set IDs
- `result_types` - JSON array of types to include

**Foundation Results**: No story relationship
- `SoilPressure`: unique_name, shell_object, min_pressure
- `VerticalDisplacement`: unique_name, label, story, min_displacement
- Cache with `result_type='SoilPressures_Min'` or `'VerticalDisplacements_Min'`

**Pushover Results**:
- `PushoverCase`: Curve metadata (result_set_id, name, direction, base_story)
- `PushoverCurvePoint`: Individual points (step_number, displacement, base_shear)
- Global results reuse story tables, distinguished by `result_set.analysis_type='Pushover'`

**Result Categories**:
- `ResultCategory`: Persistent classification for imported results (used in export discovery and reporting)

**Time-Series** (`TimeSeriesGlobalCache`):
- JSON columns: `time_steps`, `values` (arrays)
- Story ordering: ETABS exports top-to-bottom, query with `.desc()` on `story_sort_order`

**TimeHistoryData**:
- Raw time-history table for granular storage; UI currently consumes `TimeSeriesGlobalCache` for animated views

---

## 3. Database Connection Management

### Engine Registry Pattern (`database/base.py`)

```python
_project_engines: Dict[str, Engine] = {}

def _get_or_create_engine(db_path: Path) -> Engine:
    engine = create_engine(f"sqlite:///{db_path}", poolclass=NullPool)
    _project_engines[db_path_str] = engine
    return engine

def dispose_project_engine(db_path: Path) -> None:
    """Called on window close and before project deletion."""
```

**Key**: `NullPool` = connections close immediately (critical for SQLite on Windows)

---

## 4. Configuration System

### Result Type Configuration (`config/result_config.py`)

```python
RESULT_CONFIGS = {
    'Drifts_X': ResultTypeConfig(
        name='Drifts', direction='X', unit='%',
        color_scheme='blue_orange', decimal_places=3
    )
}
```

**Adding new type**:
1. Add config to `RESULT_CONFIGS`
2. Create transformer in `processing/result_transformers.py`
3. Register in `TRANSFORMERS` dict

**Color Schemes** (`utils/color_utils.py`):
- `blue_orange` - Default (low=blue, high=orange)
- `orange_blue` - Foundation results (low=orange=critical)

---

## 5. Key Patterns

### Registry Pattern (`processing/pushover/pushover_registry.py`)

```python
class PushoverRegistry:
    GLOBAL_TYPES = frozenset({"global"})
    ELEMENT_TYPES = frozenset({"wall", "beam", "column", "column_shear"})
    JOINT_TYPES = frozenset({"soil_pressure", "vert_displacement", "joint"})

    @classmethod
    def get_importer(cls, result_type: str) -> Optional[Type]:
        # Lazy-load and cache importer class
```

### Repository Pattern (`database/base_repository.py`)

```python
class BaseRepository(Generic[ModelT]):
    def get_by_id(self, id: int) -> Optional[ModelT]
    def create(self, **kwargs) -> ModelT
    def delete(self, obj: ModelT) -> None
    def list_all(self) -> List[ModelT]
```

**Specialized**: `ElementResultQueryRepository` for complex aggregation queries

### Service Layer (`services/result_service/`)

**ResultDataService** - Main facade:
- `get_standard_dataset()` - Global results
- `get_element_dataset()` - Element results
- `get_joint_dataset()` - Foundation/joint results
- `get_maxmin_dataset()` - Max/Min envelopes
- `get_comparison_dataset()` - Comparison results

**Providers** with per-dataset caching:
- `StandardDatasetProvider` (global/story-based)
- `ElementDatasetProvider` (element-specific)
- `JointDatasetProvider` (foundation/joint)

### Transformer Pattern

```python
class DriftTransformer(BaseTransformer):
    def transform(self, df: pd.DataFrame, ...) -> List[StoryDrift]:
        # Parse DataFrame, create model objects
```

Registration: `TRANSFORMERS['Drifts_X'] = DriftTransformer()`

---

## 6. Import Flow

### Standard Import
1. User selects folder → `FolderImportDialog`
2. Scan files → `ImportPreparationService` (parallel with ThreadPoolExecutor)
3. User selects cases → resolve conflicts
4. Import → `EnhancedFolderImporter` → `ExcelParser` → `TRANSFORMERS`
5. Build cache → `DataImporter._build_cache()`

### Foundation Import
- Foundation joints from "Fou" sheet propagated across all files
- Joint results stored in `JointResultsCache`

### Pushover Import (workflow enforced)
1. **Curves First**: Creates result set with name
2. **Global Results Second**: Select existing result set from combo
3. **Joints**: Auto-imported with global results (no separate dialog)

**Critical**: `session.flush()` before cache building

---

## 7. Export Flow

### Context-Aware Export
- NLTHA tab → filters `analysis_type != 'Pushover'`
- Pushover tab → filters `analysis_type == 'Pushover'`, shows Curves option

### Export Process
1. Generate single timestamp
2. Iterate result sets and types
3. Query data via service layer
4. Write files: `{result_set}_{type}_{timestamp}.xlsx`

**Type Expansion**:
- Global: `Drifts` → `Drifts_X`, `Drifts_Y`
- Element: Query cache for `_V2`, `_V3`, `_R2`, `_R3` variants
- Joint: Query for `_Min`, `_Ux`, `_Uy`, `_Uz` variants

---

## 8. UI Architecture

### Main Structure
- `MainWindow` → Project grid → `ProjectDetailWindow`
- **3-panel layout**: Browser (25%) | Content (75%)
- `ProjectDetailWindow` delegates to `window_view`, `event_handlers`, `view_loaders`, `dataset_loaders`, `import_actions`, `export_actions`, `project_data`

### Key Widgets
- `StandardResultView` - Table + Plot (directional results)
- `ComparisonResultView` - Multi-series comparison
- `MaxMinDriftsWidget` - Max/Min tables + plots
- `PushoverCurveView` - Capacity curve visualization
- `TimeSeriesAnimatedView` - 4 building profiles + playback controls

### Browser Hierarchy
```
Results
  └─ DES (result set)
      ├─ Envelopes
      │   ├─ Global Results (Drifts, Forces, etc.)
      │   ├─ Elements (Walls, Columns, Beams)
      │   └─ Joints (Soil Pressures, Vertical Displacements)
      └─ Time-Series
          └─ TH02 (load case)
              └─ Global → X/Y Direction
  └─ COM1 (comparison set)
      └─ Global/Elements/Joints → ComparisonResultView
```

### PDF Reports (`gui/reporting/`)
- `ReportWindow` - Modal dialog with checkbox tree + A4 preview
- `PDFGenerator` - High-quality PDF at 300 DPI
- `pdf_section_drawers.py` - Dedicated section renderers (e.g., pushover views)
- One section per page, debounced rendering

---

## 9. Story Ordering

| Context | Field | Notes |
|---------|-------|-------|
| Global | `Story.sort_order` | From "Story Drifts" sheet (0=bottom) |
| Per-Result | `<result>.story_sort_order` | Excel row order (0=first row) |
| Time-Series | Query `.desc()` | ETABS exports top-to-bottom |
| Quad Rotations | Always global order | Excel sorted by element name |

---

## 10. Testing

- **675 tests** (8 skipped) as of 2026-01-24
- Test organization: `tests/config/`, `tests/database/`, `tests/gui/`, `tests/processing/`, `tests/services/`, `tests/utils/`
- Full coverage for: `pushover_registry`, `data_utils`, `slug`, `env`, `pushover_utils`

---

## 11. Extension Points

### Adding Result Types
1. `RESULT_CONFIGS['NewType'] = ResultTypeConfig(...)`
2. `class NewTypeTransformer(BaseTransformer): ...`
3. `TRANSFORMERS['NewType'] = NewTypeTransformer()`

### Adding UI Views
1. Create widget extending `QWidget`
2. Add to `gui/project_detail/content.py` in `build_content_area()` and `ContentArea`
3. Wire loaders in `gui/project_detail/view_loaders.py` and tree click handlers
4. Optional: add convenience wrappers in `gui/project_detail/dataset_loaders.py`

### Adding Import Sources
1. Extend `BaseImporter`
2. Implement `import_all()` method
3. Use `session_scope()` for transactions

---

## 12. Performance

**Caching**:
- Cache tables: Wide format, indexed by result_set_id
- `ResultDataService`: Multi-level in-memory caching with LRU eviction

**Bulk Operations**:
- `bulk_create()` for batch inserts
- Session commits at end of import phase

**Lazy Loading**:
- Browser doesn't query until node clicked
- Datasets cached until invalidated

---

## 13. Known Limitations

- Single-user desktop app (no concurrent access)
- SQLite limits (no server-side processing)
- Element results limited to piers
- Time-series: global results only (element-level future)

---

**For quick tasks, see CLAUDE.md**
**For design patterns, see DESIGN.md**
