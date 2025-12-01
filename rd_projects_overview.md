# R&D Roadmap: Strategic Initiatives & Pilot Projects

## **Summary of Research Directions**
1. **Contextual Access to Structural Engineering Knowledge** – A curated, structured, multi-layer knowledge base enriched with semantic LLM reasoning and vector-embedding retrieval, enabling transparent and authoritative access to structural-engineering knowledge.
2. **Advanced & Data-Heavy Structural Engineering Tools** – A unified ecosystem for processing, analysing, and visualising structural-engineering data, addressing limitations of current fragmented, slow, or manual workflows.
3. **Multiphysics & Parametric Analysis Pipeline with ML Integration** – A modular, multi-solver orchestration pipeline enabling robust parametric studies, solver translation, numerical-stability automation, and ML-driven optimisation.

---

## **Projected User Stories**
These user-story style narratives illustrate how engineers, researchers, and practitioners would interact with the ecosystem once the three strategic initiatives are mature. They demonstrate workflow transformation, friction reduction, and the value of unified digitalisation.

### **1. Knowledge Access User Story**
*A structural engineer preparing a retrofit concept for an irregular RC building uploads sketches and a paragraph describing torsional irregularity. The system identifies the governing mechanics, retrieves relevant research precedent, cites sections from standards, surfaces appropriate damping/ductility models, and links publicly available PDFs. It also lists laboratories and researchers who published on torsional response modelling.*

### **2. Data-Heavy Tools User Story**
*During nonlinear dynamic analysis, an engineer selects a target spectrum and requests a set of ground motions. The GMP tool filters thousands of records based on metadata, performs optimisation-based scaling, visualises spectra, highlights outliers, and exports a ready-to-use suite. After running the structural model, the RPS tool automatically ingests results, creates envelopes, flags anomalous demands, clusters response trends, and generates a polished technical report.*

### **3. Multiphysics Pipeline User Story**
*A research engineer models a concept in ETABS, then launches a parametric sweep. The pipeline automatically translates the model to OpenSees for NLTHA and to Abaqus for local plastic hinge verification. Numerical instabilities appear in a subset of simulations; automatic iteration agents refine meshes, adjust damping, and resolve convergence issues. After simulations complete, the ML layer builds a surrogate model identifying the most influential parameters and suggests optimal design ranges.*

---

## 1. Contextual Access to Structural Engineering Knowledge

### **Problem Statement**
Structural engineering knowledge is distributed across journals, standards, guidelines, reports, and proprietary documents. Accessing relevant information requires significant manual effort, lacks structure, and does not leverage modern retrieval or reasoning techniques.

### **Vision**
Create a high-fidelity structural-engineering knowledge system built on curated, structured, and hierarchically classified sources, enhanced with vector-embedding search and LLM-driven contextual reasoning. The system enables engineers to query complex problems and receive transparent, authoritative, and source-linked responses.

### **Technical Approach**
- Develop a **multi-layered knowledge graph** that maps structural-engineering domains, subdomains, entities, and document metadata.
- Integrate **LLM-supported retrieval** combining structured filters, vector embeddings, and context-aware reasoning.
- Provide **direct links to publicly available PDFs** or user-owned documents for proprietary or licensed sources.
- Offer **traceable outputs** with cited excerpts and provenance paths.
- Maintain a **schema-driven ingestion framework** for journals, standards, guidelines, reports, and future content types (materials, suppliers, test data).

### **Current Status**
- Not implemented in the current GMP codebase; there are no knowledge-graph models, ingestion pipelines, or publication retrieval endpoints.
- Frontend screens are focused on GMP records/projects flows; no knowledge-base search UI or LLM chat tied to data exists yet.
- Backend services are dedicated to ground-motion APIs (Postgres + Mongo); `/publications` and related schemas/routes are absent.

### **Next Steps**
- Add semantic embeddings with hybrid lexical-semantic retrieval.
- Extend ingestion to materials databases and supplier/service metadata.
- Implement user-owned document ingestion with private embedding spaces.
- Develop advanced LLM reasoning modes (comparative synthesis, precedent extraction).

---

## 2. Advanced & Data-Heavy Structural Engineering Tools

### **Problem Statement**
Current tools for ground-motion processing, nonlinear structural analysis, and postprocessing are fragmented across heterogeneous software ecosystems. Engineers face inefficiencies, lack of automation, inconsistent outputs, and limited visualisation capabilities.

### **Vision**
Modernise and unify data-heavy structural-engineering workflows by creating a consistent suite of tools for ground-motion selection, scaling, analysis processing, and statistical evaluation with high-quality visualisation and reproducible pipelines.

### **Technical Approach**
- Develop a **Ground Motion Processing Tool (GMP)** supporting:
  - seismological and metadata-based filtering, including magnitude, distance, mechanism, Vs30 (shear-wave velocity to 30 m), duration, and spectral shape.
  - optimisation-based scaling using MSE/RMSPE criteria.
  - rich time-history and spectral visualisation.
  - automated reporting and reproducible suite exports.
- Develop **Results Processing & Visualisation Tools (RPS)** supporting:
  - ingestion of outputs from ETABS, SAP2000, OpenSees, Abaqus, and similar tools.
  - a unified database-centric results-schema.
  - envelope plots, demand-capacity charts, distributions, cluster analysis, and outlier detection.
  - automated reporting and structured exports.
- Ensure consistent **design language, data-model alignment, and workflow reproducibility**.

### **Current Status**
- PyQt6 desktop client with modern dark UI (Home, Projects grid, Project Detail), HiDPI-safe, Windows App ID/icons, and web-inspired styling.
- Local storage: per-project SQLite databases with a catalog; SQLAlchemy models for stories, load cases, global/element/joint results; cache tables for fast plotting; Alembic migrations tracked.
- Import pipeline: single-file and folder imports with prescan and conflict handling; supports Story Drifts, Diaphragm Accelerations, Story Forces, Floors Displacements (from Joint Displacements), Pier Forces, Column Forces (V2/V3), Column Axials, Column/Beam/Quad Rotations, Soil Pressures, and Vertical Displacements; automatic result-set/category creation, duplicate checks, and post-import cache generation.
- Visualization: tree-based browser of result sets; global envelopes and element/joint views; max/min summaries; PyQtGraph profile and scatter plots; comparison sets across result sets (drifts, accelerations, forces, displacements, rotations) and “All Rotations” views.
- Project ops and export: create/import/export projects; safe deletion with engine disposal; export dialogs with MVP Excel/CSV export service; hot‑reload dev runner; PyInstaller spec and Windows build scripts.

### **Next Steps**
- Extend optimisation algorithms for record scaling.
- Finalise project-templating and reproducibility layers.
- Add statistical-learning modules for response clustering and anomaly detection.
- Integrate both tools under a unified interface with shared data contracts.

---

## 3. Multiphysics & Parametric Analysis Pipeline with ML Integration

### **Problem Statement**
Structural engineering analyses—especially nonlinear, multiphysics, or parametric studies—require multiple solvers, manual translation, iterative adjustments, and repeated trial-and-error to achieve convergence or stable numerical behaviour.

### **Vision**
Develop a modular, tool-agnostic pipeline capable of orchestrating conceptual modelling, solver translation, advanced simulations, postprocessing, and ML-enhanced automation across multiple software platforms.

### **Technical Approach**
- **Conceptual & Parametric Modelling Layer**
  - Use fast modelling tools (ETABS, SAP2000, Grasshopper, custom Python/OpenSees wrappers) for conceptual definitions.
  - Export into a neutral schema for downstream processing.

- **Model Translation Layer**
  - Translate conceptual models into solver-specific formats for Abaqus, OpenSees, ANSYS, LS-DYNA, and others.
  - Support multiple solvers per analysis type.

- **Advanced Multiphysics / Nonlinear Analysis**
  - Select the most suitable solver for each physics domain.
  - Perform nonlinear, SSI, FSI, thermal-structural, or detailed local FE analyses.

- **Iterative Modelling & Numerical Robustness Automation**
  - Automate steps such as:
    - mesh refinement,
    - timestep and damping adjustments,
    - convergence-tolerance tuning,
    - hinge/contact property adjustments,
    - detection and mitigation of non-physical responses.

- **Postprocessing & Feature Extraction**
  - Standardise outputs across solvers.
  - Extract domain-specific features for analysis, ML, and optimisation.

- **ML & Agentic Layer**
  - Develop surrogate models for expensive simulations.
  - Implement RL/agentic loops for parameter tuning or mesh refinement.
  - Integrate robust anomaly detectors for solver warnings or instabilities.

### **Current Status**
- No multiphysics orchestration implemented in this repo; there is no neutral schema, solver translators, or batch/parametric runner beyond the GMP ground-motion workflow.
- Existing capabilities focus solely on ground-motion processing; no Abaqus/OpenSees/ANSYS connectors or ML surrogate training code is present.
- Monitoring/ops foundations could host future services, but the multiphysics pipeline remains at the ideation stage.

### **Next Steps**
- Complete cross-solver translation layer.
- Build orchestration engine for parametric and batch simulations.
- Add iteration controllers (agents) for automatic robustness adjustments.
- Integrate ML training pipeline for surrogate modelling and optimisation.

---
