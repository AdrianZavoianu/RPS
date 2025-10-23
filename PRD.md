# Product Requirements Document (PRD)
## Results Processing System (RPS)

**Version**: 1.0
**Last Updated**: 2025-10-23
**Status**: Production-ready with core visualization features

---

## 1. Product Overview

### 1.1 Purpose

Results Processing System (RPS) is a desktop application designed for structural engineers to process, organize, and visualize analysis results from ETABS and SAP2000 Excel exports. The application provides an efficient workflow for managing multiple projects, analyzing structural performance data, and generating visualizations for engineering review.

### 1.2 Target Users

- **Primary**: Structural engineers working with ETABS/SAP2000
- **Secondary**: Engineering managers reviewing analysis results
- **Tertiary**: Technical staff performing data quality checks

### 1.3 Key Benefits

- **Centralized Data Management**: Store all project results in organized SQLite databases
- **Fast Import**: Batch import multiple Excel files from folders with progress tracking
- **Interactive Visualization**: High-performance building profile plots using PyQtGraph
- **Intuitive Navigation**: Hierarchical browser for exploring results by type and envelope
- **Consistent UI**: Modern dark theme matching GMP design system

---

## 2. Core Features (Production)

### 2.1 Project Management

**FR-001: Project Cards Display**
- Display all projects as cards in a grid layout
- Show project name, description, creation date, and last updated date
- Provide "Open Project" action on each card
- Support multiple projects in the system

**FR-002: Project Detail View**
- Open individual project in dedicated window
- Display 3-panel layout: Browser | Table | Plot
- Navigate back to main window via header

### 2.2 Data Import

**FR-003: Single File Import**
- Import single Excel file via File → Import dialog
- Parse ETABS/SAP2000 formatted Excel files
- Extract data from multiple sheets:
  - Story Drifts
  - Story Accelerations
  - Story Forces
- Auto-detect load cases (TH01-THnn, MCR1-MCR6)
- Auto-detect story names and elevations
- Store results in normalized database schema

**FR-004: Folder Batch Import**
- Import all Excel files from a selected folder (recursive)
- Display progress dialog with real-time updates
- Prefix load case names with filename to avoid conflicts
- Continue processing on individual file errors
- Generate wide-format cache after import completes
- Show success/failure summary

**FR-005: Data Validation**
- Validate Excel sheet names and column headers
- Skip header rows (rows 0, 2) during parsing
- Handle missing or malformed data gracefully
- Provide error messages for invalid files

### 2.3 Results Visualization

**FR-006: Results Tree Browser**
- Hierarchical navigation: Envelopes → Result Types
- Three main result types: Drifts, Accelerations, Forces
- Select result type to update table and plot
- Fixed 200px width, collapsible tree structure

**FR-007: Results Table Display**
- Compact table with auto-calculated width
- Columns: Story, Load Cases (TH01-THnn), Avg, Max, Min
- Direction-specific filtering (X for Drifts, UX for Accelerations, VX for Forces)
- Unit conversion and formatting:
  - Drifts: Percentage with 2 decimals (1.23%)
  - Accelerations: g-units with 3 decimals (0.123g)
  - Forces: kN with 1 decimal (123.4kN)
- Color-coded gradient for load case columns (blue → orange)
- Fixed column widths: 70px for Story, 55px for data
- Sortable by Story column (click header to toggle)

**FR-008: Building Profile Plot**
- Horizontal layout: Value (X-axis) vs. Story Height (Y-axis)
- One line per load case (13 colors cycling)
- Bold dashed average line in teal
- Dark theme (#0a0c10 background, grid alpha 0.2)
- Auto-scaled axes with padding
- Title and axis labels from configuration
- Interactive: hover, zoom, pan (PyQtGraph features)

**FR-009: Interactive Column Selection**
- Click load case column header to select/deselect
- Highlight selected columns in table header (darker accent)
- Update plot to show only selected load cases
- Support multiple selection
- Clear selection by clicking again

**FR-010: Hover Effects**
- Hover over column header to preview in plot
- Highlight corresponding line in plot
- Clear highlight when mouse leaves header

### 2.4 Data Processing

**FR-011: Result Type Configurations**
- Centralized configuration for each result type
- Define: direction suffix, unit, decimals, multiplier, plot mode, color scheme
- Easy to add new result types (5-10 lines of code)

**FR-012: Data Transformations**
- Filter columns by direction (X, UX, VX)
- Clean column names (extract load case from full column name)
- Calculate statistics: Avg, Max, Min across load cases
- Pluggable transformer pattern for extensibility

**FR-013: Wide-Format Cache**
- Store denormalized data for fast table display
- JSON column with load case → value mappings
- No JOIN queries needed for display
- Auto-generated during folder import

---

## 3. Data Model

### 3.1 Core Entities

**Projects**
- Represents engineering projects
- Fields: ID, Name, Description, Created At, Updated At
- One project can have multiple load cases, stories, and result sets

**Load Cases**
- Analysis cases (TH01, TH02, MCR1, etc.)
- Fields: ID, Project ID, Name, Case Type, Description
- Linked to multiple result records (drifts, accelerations, forces)

**Stories**
- Building floors/levels
- Fields: ID, Project ID, Name, Elevation, Sort Order
- Linked to result records for each story

**Result Sets**
- Collections of related results (DES, MCE, etc.)
- Fields: ID, Project ID, Name, Result Category, Description
- Groups analysis results together (e.g., all DES envelope results)

**Global Results Cache**
- Wide-format cache for fast table display
- Fields: ID, Project ID, Result Set ID, Result Type, Story ID, Results Matrix (JSON)
- Optimized for visualization performance

**Result Tables** (Normalized)
- Story Drifts (X and Y directions)
- Story Accelerations (UX and UY, in g-units)
- Story Forces (VX and VY)

### 3.2 Data Relationships

```
Projects
  ├── Load Cases
  ├── Stories
  ├── Result Sets
  │   └── Global Results Cache
  └── Results (Drifts, Accelerations, Forces)
```

### 3.3 Data Flow

1. **Import**: Excel File → Parser → Processor → Database (Normalized)
2. **Cache Generation**: Normalized DB → Cache Builder → Wide-Format Cache
3. **Display**: Cache → Table/Plot Widgets → User Interface

---

## 4. User Workflows

### 4.1 First-Time Setup

1. Launch RPS application
2. See empty project grid with welcome message
3. Click "Import from Folder" to load first project
4. Browse to folder containing Excel files
5. Wait for import progress (see file count updates)
6. View newly created project card
7. Click "Open Project" to explore results

### 4.2 Daily Usage - Viewing Results

1. Launch RPS application
2. See project cards for existing projects
3. Click "Open Project" on desired card
4. Review results in 3-panel layout:
   - Left: Browse to Envelopes → Drifts
   - Center: Review story drift table
   - Right: Analyze building profile plot
5. Select load case columns to isolate specific cases
6. Hover over headers to preview lines
7. Navigate to Accelerations or Forces as needed

### 4.3 Adding New Project Data

1. Open project detail window
2. Click "Load Data" button
3. Browse to folder with new Excel files
4. Monitor import progress
5. Wait for cache generation
6. Results browser updates automatically
7. Select new result set to view data

### 4.4 Comparing Load Cases

1. Open project detail window
2. Navigate to Drifts (or other result type)
3. Click multiple load case column headers to select
4. Plot updates to show only selected cases
5. Compare colored lines in building profile
6. Review Avg/Max/Min statistics in table

---

## 5. Technical Requirements

### 5.1 Performance

- **TR-001**: Import 10 Excel files (100 rows each) in < 30 seconds
- **TR-002**: Display table with 50 stories and 20 load cases in < 1 second
- **TR-003**: Plot building profile with 20 lines in < 500ms
- **TR-004**: Support 100k+ data points in PyQtGraph plots
- **TR-005**: Respond to column selection within 200ms

### 5.2 Compatibility

- **TR-006**: Run on Windows 10 and Windows 11
- **TR-007**: Parse ETABS 19+ Excel exports
- **TR-008**: Parse SAP2000 23+ Excel exports
- **TR-009**: Handle Excel files up to 50MB
- **TR-010**: Support .xlsx and .xls formats

### 5.3 Usability

- **TR-011**: Dark Windows title bar (Windows 10 build 19041+)
- **TR-012**: GMP-exact design system (colors, typography, buttons)
- **TR-013**: Hot-reload development environment (watchfiles)
- **TR-014**: Clear error messages for invalid inputs
- **TR-015**: Responsive UI (no freezing during import)

### 5.4 Data Integrity

- **TR-016**: Database transactions with rollback on error
- **TR-017**: Foreign key constraints enforced
- **TR-018**: Bulk insert for performance
- **TR-019**: Database migrations with Alembic
- **TR-020**: Backup-friendly SQLite format

---

## 6. Future Enhancements (Roadmap)

### 6.1 Phase 2: Additional Result Types

- **FE-001**: Joint Displacements visualization
- **FE-002**: Joint Reactions visualization
- **FE-003**: Element Forces (Columns, Beams, Links)
- **FE-004**: Pier Forces visualization
- **FE-005**: Plastic Hinge States display

### 6.2 Phase 3: Time-Series Visualization

- **FE-006**: Time-history plots for dynamic analysis
- **FE-007**: Animation controls (play, pause, scrub)
- **FE-008**: Compare time-series across load cases
- **FE-009**: Export time-series to video

### 6.3 Phase 4: Statistical Analysis

- **FE-010**: Multi-project comparison tables
- **FE-011**: Statistical summaries (mean, std dev, percentiles)
- **FE-012**: Custom filters and queries
- **FE-013**: Data export to CSV/Excel
- **FE-014**: Custom report generation (PDF)

### 6.4 Phase 5: 3D Visualization

- **FE-015**: Load building geometry from ETABS/SAP2000
- **FE-016**: Overlay results on 3D model
- **FE-017**: Interactive 3D navigation (rotate, zoom, pan)
- **FE-018**: Color-coded building visualization by result magnitude
- **FE-019**: Animation of dynamic response on 3D model

### 6.5 Phase 6: Advanced Features

- **FE-020**: Cloud storage integration (optional)
- **FE-021**: Collaborative review and comments
- **FE-022**: Custom result type definitions
- **FE-023**: Automated report templates
- **FE-024**: API for external tool integration

---

## 7. Constraints and Assumptions

### 7.1 Constraints

- **Desktop-only**: No web version planned (PyQt6 limitation)
- **Windows-focused**: Primary platform, WSL/Linux for development only
- **Local storage**: SQLite databases stored on local disk
- **Single-user**: No multi-user collaboration features
- **English-only**: No internationalization in Phase 1

### 7.2 Assumptions

- Users have ETABS or SAP2000 licenses
- Users export results to Excel format (standard ETABS/SAP2000 feature)
- Excel files follow standard ETABS/SAP2000 formatting
- Users have Windows machines with Python 3.11+
- Users have basic understanding of structural analysis results

---

## 8. Success Metrics

### 8.1 Adoption

- **SM-001**: 80% of structural engineering team using RPS within 3 months
- **SM-002**: Average 5 projects per user
- **SM-003**: Average 2-3 sessions per week per user

### 8.2 Efficiency

- **SM-004**: Reduce results review time by 50% compared to manual Excel review
- **SM-005**: 90% of imports complete without errors
- **SM-006**: Users rate UI as "good" or "excellent" (survey)

### 8.3 Reliability

- **SM-007**: Zero data loss incidents
- **SM-008**: < 5% of imports require troubleshooting
- **SM-009**: Application crash rate < 0.1% of sessions

---

## 9. Out of Scope (Phase 1)

The following features are explicitly **not included** in the current production release:

- Web-based interface
- Multi-user collaboration
- Cloud storage
- Mobile applications
- Real-time syncing across devices
- Custom scripting/automation
- Integration with other analysis software (beyond ETABS/SAP2000 Excel exports)
- Advanced statistical modeling (regression, ML predictions)
- Report generation beyond manual screenshot/export
- Time-series visualization (animation, video export)
- 3D building model display
- Element-level result visualization
- Plastic hinge state display

---

## 10. Glossary

| Term | Definition |
|------|------------|
| **ETABS** | Engineering software for structural analysis and design of buildings |
| **SAP2000** | General structural analysis software |
| **Load Case** | Specific loading scenario in analysis (e.g., TH01 = Time History 1) |
| **Story** | Building floor or level |
| **Drift** | Lateral displacement between consecutive floors (percentage) |
| **Acceleration** | Floor acceleration in g-units (multiples of gravity) |
| **Envelope** | Maximum/minimum values across all time steps |
| **Time History** | Dynamic analysis results over time |
| **Modal Combination** | Combination of multiple vibration modes (MCR1, MCR2, etc.) |
| **Result Set** | Collection of related analysis results (DES, MCE, etc.) |
| **Wide-Format Cache** | Denormalized database table optimized for fast display |
| **PyQtGraph** | High-performance plotting library for Python |
| **GMP Design System** | Design system for consistent UI styling |

---

## Appendix A: Example Excel File Structure

**Sheet: Story Drifts**
```
Row 0: [Headers - skipped]
Row 1: Story, 160Wil_DES_Global_TH01_X, 160Wil_DES_Global_TH02_X, ...
Row 2: [Subheaders - skipped]
Row 3: Story 1, 0.0123, 0.0145, ...
Row 4: Story 2, 0.0098, 0.0112, ...
...
```

**Sheet: Story Accelerations**
```
Row 0: [Headers - skipped]
Row 1: Story, 160Wil_DES_Global_TH01_UX, 160Wil_DES_Global_TH02_UX, ...
Row 2: [Subheaders - skipped]
Row 3: Story 1, 1234.5, 1456.2, ...  (mm/s²)
...
```

**Sheet: Story Forces**
```
Row 0: [Headers - skipped]
Row 1: Story, 160Wil_DES_Global_TH01_VX, 160Wil_DES_Global_TH02_VX, ...
Row 2: [Subheaders - skipped]
Row 3: Story 1, 12345.6, 13456.7, ...  (kN)
...
```

---

**Document Approval**

| Role | Name | Date | Signature |
|------|------|------|-----------|
| Product Owner | [Name] | [Date] | [Signature] |
| Engineering Lead | [Name] | [Date] | [Signature] |
| QA Lead | [Name] | [Date] | [Signature] |

---

**Revision History**

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2025-10-23 | Claude Code | Initial consolidated PRD |
