"""SQLAlchemy database models for structural engineering results."""

from sqlalchemy import (
    Column,
    Integer,
    String,
    Float,
    DateTime,
    ForeignKey,
    Text,
    Index,
    JSON,
)
from sqlalchemy.orm import relationship
from datetime import datetime

from .base import Base


class Project(Base):
    """Represents an engineering project."""

    __tablename__ = "projects"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False, unique=True)
    description = Column(Text, nullable=True)
    analysis_type = Column(String(50), nullable=True, default='NLTHA')  # 'NLTHA', 'Pushover', or 'Mixed'
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    load_cases = relationship("LoadCase", back_populates="project", cascade="all, delete-orphan")
    stories = relationship("Story", back_populates="project", cascade="all, delete-orphan")
    result_sets = relationship("ResultSet", back_populates="project", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Project(id={self.id}, name='{self.name}')>"


class LoadCase(Base):
    """Represents a load case or analysis case (e.g., TH01, MCR1)."""

    __tablename__ = "load_cases"

    id = Column(Integer, primary_key=True, autoincrement=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    name = Column(String(100), nullable=False)
    case_type = Column(String(50), nullable=True)  # e.g., 'Time History', 'Modal', 'Static'
    description = Column(Text, nullable=True)

    # Relationships
    project = relationship("Project", back_populates="load_cases")
    story_drifts = relationship("StoryDrift", back_populates="load_case", cascade="all, delete-orphan")
    story_accelerations = relationship("StoryAcceleration", back_populates="load_case", cascade="all, delete-orphan")
    story_forces = relationship("StoryForce", back_populates="load_case", cascade="all, delete-orphan")
    story_displacements = relationship("StoryDisplacement", back_populates="load_case", cascade="all, delete-orphan")
    wall_shears = relationship("WallShear", cascade="all, delete-orphan")
    column_shears = relationship("ColumnShear", cascade="all, delete-orphan")
    column_rotations = relationship("ColumnRotation", cascade="all, delete-orphan")

    # Composite unique constraint
    __table_args__ = (Index("ix_project_loadcase", "project_id", "name", unique=True),)

    def __repr__(self):
        return f"<LoadCase(id={self.id}, name='{self.name}')>"


class Story(Base):
    """Represents a building story/floor."""

    __tablename__ = "stories"

    id = Column(Integer, primary_key=True, autoincrement=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    name = Column(String(100), nullable=False)
    elevation = Column(Float, nullable=True)
    sort_order = Column(Integer, nullable=True)  # For ordering floors

    # Relationships
    project = relationship("Project", back_populates="stories")
    drifts = relationship("StoryDrift", back_populates="story", cascade="all, delete-orphan")
    accelerations = relationship("StoryAcceleration", back_populates="story", cascade="all, delete-orphan")
    forces = relationship("StoryForce", back_populates="story", cascade="all, delete-orphan")
    displacements = relationship("StoryDisplacement", back_populates="story", cascade="all, delete-orphan")

    # Composite unique constraint
    __table_args__ = (Index("ix_project_story", "project_id", "name", unique=True),)

    def __repr__(self):
        return f"<Story(id={self.id}, name='{self.name}')>"


class StoryDrift(Base):
    """Story drift results."""

    __tablename__ = "story_drifts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    story_id = Column(Integer, ForeignKey("stories.id"), nullable=False)
    load_case_id = Column(Integer, ForeignKey("load_cases.id"), nullable=False)
    result_category_id = Column(Integer, ForeignKey("result_categories.id"), nullable=True)
    direction = Column(String(10), nullable=False)  # 'X' or 'Y'
    drift = Column(Float, nullable=False)
    max_drift = Column(Float, nullable=True)  # Maximum across all points
    min_drift = Column(Float, nullable=True)  # Minimum across all points
    story_sort_order = Column(Integer, nullable=True)  # Story order from source sheet (Story Drifts)

    # Relationships
    story = relationship("Story", back_populates="drifts")
    load_case = relationship("LoadCase", back_populates="story_drifts")
    result_category = relationship("ResultCategory", back_populates="drifts")

    # Indexes for fast querying
    __table_args__ = (
        Index("ix_drift_story_case", "story_id", "load_case_id", "direction"),
        Index("ix_drift_category", "result_category_id"),
    )

    def __repr__(self):
        return f"<StoryDrift(story_id={self.story_id}, case={self.load_case_id}, dir={self.direction}, drift={self.drift})>"


class StoryAcceleration(Base):
    """Story acceleration results."""

    __tablename__ = "story_accelerations"

    id = Column(Integer, primary_key=True, autoincrement=True)
    story_id = Column(Integer, ForeignKey("stories.id"), nullable=False)
    load_case_id = Column(Integer, ForeignKey("load_cases.id"), nullable=False)
    result_category_id = Column(Integer, ForeignKey("result_categories.id"), nullable=True)
    direction = Column(String(10), nullable=False)  # 'UX' or 'UY'
    acceleration = Column(Float, nullable=False)  # In g units
    max_acceleration = Column(Float, nullable=True)
    min_acceleration = Column(Float, nullable=True)
    story_sort_order = Column(Integer, nullable=True)  # Story order from source sheet (Story Accelerations)

    # Relationships
    story = relationship("Story", back_populates="accelerations")
    load_case = relationship("LoadCase", back_populates="story_accelerations")
    result_category = relationship("ResultCategory", back_populates="accelerations")

    # Indexes
    __table_args__ = (
        Index("ix_accel_story_case", "story_id", "load_case_id", "direction"),
        Index("ix_accel_category", "result_category_id"),
    )

    def __repr__(self):
        return f"<StoryAcceleration(story_id={self.story_id}, case={self.load_case_id}, accel={self.acceleration}g)>"


class StoryForce(Base):
    """Story shear force results."""

    __tablename__ = "story_forces"

    id = Column(Integer, primary_key=True, autoincrement=True)
    story_id = Column(Integer, ForeignKey("stories.id"), nullable=False)
    load_case_id = Column(Integer, ForeignKey("load_cases.id"), nullable=False)
    result_category_id = Column(Integer, ForeignKey("result_categories.id"), nullable=True)
    direction = Column(String(10), nullable=False)  # 'VX' or 'VY'
    location = Column(String(20), nullable=True)  # 'Top' or 'Bottom'
    force = Column(Float, nullable=False)
    max_force = Column(Float, nullable=True)
    min_force = Column(Float, nullable=True)
    story_sort_order = Column(Integer, nullable=True)  # Story order from source sheet (Story Forces)

    # Relationships
    story = relationship("Story", back_populates="forces")
    load_case = relationship("LoadCase", back_populates="story_forces")
    result_category = relationship("ResultCategory", back_populates="forces")

    # Indexes
    __table_args__ = (
        Index("ix_force_story_case", "story_id", "load_case_id", "direction"),
        Index("ix_force_category", "result_category_id"),
    )

    def __repr__(self):
        return f"<StoryForce(story_id={self.story_id}, case={self.load_case_id}, force={self.force})>"


class StoryDisplacement(Base):
    """Story displacement results."""

    __tablename__ = "story_displacements"

    id = Column(Integer, primary_key=True, autoincrement=True)
    story_id = Column(Integer, ForeignKey("stories.id"), nullable=False)
    load_case_id = Column(Integer, ForeignKey("load_cases.id"), nullable=False)
    result_category_id = Column(Integer, ForeignKey("result_categories.id"), nullable=True)
    direction = Column(String(10), nullable=False)  # 'UX', 'UY', 'UZ'
    displacement = Column(Float, nullable=False)
    max_displacement = Column(Float, nullable=True)
    min_displacement = Column(Float, nullable=True)
    story_sort_order = Column(Integer, nullable=True)  # Story order from source sheet (Joint DisplacementsG)

    # Relationships
    story = relationship("Story", back_populates="displacements")
    load_case = relationship("LoadCase", back_populates="story_displacements")
    result_category = relationship("ResultCategory", back_populates="displacements")

    # Indexes
    __table_args__ = (
        Index("ix_disp_story_case", "story_id", "load_case_id", "direction"),
        Index("ix_disp_category", "result_category_id"),
    )

    def __repr__(self):
        return f"<StoryDisplacement(story_id={self.story_id}, case={self.load_case_id}, disp={self.displacement})>"


# Additional models for future expansion

class Element(Base):
    """Base table for structural elements (columns, beams, piers, etc.)."""

    __tablename__ = "elements"

    id = Column(Integer, primary_key=True, autoincrement=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    element_type = Column(String(50), nullable=False)  # 'Wall', 'Column', 'Beam', 'Pier', 'Link'
    name = Column(String(100), nullable=False)
    unique_name = Column(String(100), nullable=True)  # From ETABS/SAP2000
    story_id = Column(Integer, ForeignKey("stories.id"), nullable=True)

    # Relationships
    wall_shears = relationship("WallShear", back_populates="element", cascade="all, delete-orphan")
    column_shears = relationship("ColumnShear", cascade="all, delete-orphan")
    column_axials = relationship("ColumnAxial", cascade="all, delete-orphan")
    column_rotations = relationship("ColumnRotation", cascade="all, delete-orphan")
    quad_rotations = relationship("QuadRotation", back_populates="element", cascade="all, delete-orphan")

    # Composite unique constraint
    __table_args__ = (
        Index("ix_project_element", "project_id", "element_type", "unique_name", unique=True),
    )

    def __repr__(self):
        return f"<Element(id={self.id}, type='{self.element_type}', name='{self.name}')>"


class TimeHistoryData(Base):
    """Time-history data for detailed analysis (optimized for large datasets)."""

    __tablename__ = "time_history_data"

    id = Column(Integer, primary_key=True, autoincrement=True)
    load_case_id = Column(Integer, ForeignKey("load_cases.id"), nullable=False)
    element_id = Column(Integer, ForeignKey("elements.id"), nullable=True)
    story_id = Column(Integer, ForeignKey("stories.id"), nullable=True)
    result_type = Column(String(50), nullable=False)  # 'Drift', 'Acceleration', 'Force', etc.
    time_step = Column(Float, nullable=False)
    value = Column(Float, nullable=False)
    direction = Column(String(10), nullable=True)

    # Indexes for fast time-series queries
    __table_args__ = (
        Index("ix_timehist_case_result", "load_case_id", "result_type"),
        Index("ix_timehist_element", "element_id"),
    )

    def __repr__(self):
        return f"<TimeHistoryData(case={self.load_case_id}, t={self.time_step}, val={self.value})>"


class ResultSet(Base):
    """Represents a collection of results (DES, MCE, etc.) for organizing analysis outputs."""

    __tablename__ = "result_sets"

    id = Column(Integer, primary_key=True, autoincrement=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    name = Column(String(100), nullable=False)  # 'DES', 'MCE', 'SLE', etc.
    description = Column(Text, nullable=True)
    analysis_type = Column(String(50), nullable=True, default='NLTHA')  # 'NLTHA' or 'Pushover'
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    project = relationship("Project", back_populates="result_sets")
    categories = relationship("ResultCategory", back_populates="result_set", cascade="all, delete-orphan")
    cache_entries = relationship("GlobalResultsCache", back_populates="result_set", cascade="all, delete-orphan")

    # Composite unique constraint
    __table_args__ = (Index("ix_project_resultset", "project_id", "name", unique=True),)

    def __repr__(self):
        return f"<ResultSet(id={self.id}, name='{self.name}')>"


class ComparisonSet(Base):
    """Represents a comparison between multiple result sets (e.g., COM1: DES vs MCE)."""

    __tablename__ = "comparison_sets"

    id = Column(Integer, primary_key=True, autoincrement=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    name = Column(String(100), nullable=False)  # 'COM1', 'COM2', etc.
    description = Column(Text, nullable=True)
    result_set_ids = Column(JSON, nullable=False)  # List of result set IDs to compare [1, 2, 3]
    result_types = Column(JSON, nullable=False)  # List of result types to include ['Drifts', 'Forces', etc.]
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    project = relationship("Project", backref="comparison_sets")

    # Composite unique constraint
    __table_args__ = (Index("ix_project_comparisonset", "project_id", "name", unique=True),)

    def __repr__(self):
        return f"<ComparisonSet(id={self.id}, name='{self.name}')>"


class ResultCategory(Base):
    """Represents a category within a result set (Envelopes/Time-Series → Global/Elements/Joints)."""

    __tablename__ = "result_categories"

    id = Column(Integer, primary_key=True, autoincrement=True)
    result_set_id = Column(Integer, ForeignKey("result_sets.id"), nullable=False)
    category_name = Column(String(50), nullable=False)  # 'Envelopes', 'Time-Series'
    category_type = Column(String(50), nullable=False)  # 'Global', 'Elements', 'Joints'

    # Relationships
    result_set = relationship("ResultSet", back_populates="categories")
    drifts = relationship("StoryDrift", back_populates="result_category", cascade="all, delete-orphan")
    accelerations = relationship("StoryAcceleration", back_populates="result_category", cascade="all, delete-orphan")
    forces = relationship("StoryForce", back_populates="result_category", cascade="all, delete-orphan")
    displacements = relationship("StoryDisplacement", back_populates="result_category", cascade="all, delete-orphan")
    wall_shears = relationship("WallShear", cascade="all, delete-orphan")
    column_shears = relationship("ColumnShear", cascade="all, delete-orphan")
    column_rotations = relationship("ColumnRotation", cascade="all, delete-orphan")

    # Composite unique constraint
    __table_args__ = (
        Index("ix_resultset_category", "result_set_id", "category_name", "category_type", unique=True),
    )

    def __repr__(self):
        return f"<ResultCategory(id={self.id}, set='{self.result_set_id}', name='{self.category_name}', type='{self.category_type}')>"


class GlobalResultsCache(Base):
    """Wide-format cache for storey-level results optimized for tabular display.

    One row per story, with all load cases stored as JSON for fast retrieval.
    Format: {"TH01_X": 0.0023, "TH01_Y": 0.0019, "MCR1_X": 0.0021, ...}
    """

    __tablename__ = "global_results_cache"

    id = Column(Integer, primary_key=True, autoincrement=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    result_set_id = Column(Integer, ForeignKey("result_sets.id"), nullable=True)
    result_type = Column(String(50), nullable=False)  # 'Drifts', 'Accelerations', 'Forces'
    story_id = Column(Integer, ForeignKey("stories.id"), nullable=False)

    # Wide-format data stored as JSON
    results_matrix = Column(JSON, nullable=False)

    # Story ordering from source sheet (each result type preserves its own sheet order)
    story_sort_order = Column(Integer, nullable=True)

    # Metadata
    last_updated = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    result_set = relationship("ResultSet", back_populates="cache_entries")

    # Composite index for fast lookups
    __table_args__ = (
        Index("ix_cache_lookup", "project_id", "result_set_id", "result_type"),
        Index("ix_cache_story", "story_id"),
    )

    def __repr__(self):
        return f"<GlobalResultsCache(project_id={self.project_id}, type='{self.result_type}', story_id={self.story_id})>"


class AbsoluteMaxMinDrift(Base):
    """Stores absolute maximum drifts comparing Max and Min values for each load case.

    For each load case and direction, stores:
    - The absolute maximum drift (larger of |Max| or |Min|)
    - Whether it was positive (+) or negative (-)
    """

    __tablename__ = "absolute_maxmin_drifts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    result_set_id = Column(Integer, ForeignKey("result_sets.id"), nullable=False)
    story_id = Column(Integer, ForeignKey("stories.id"), nullable=False)
    load_case_id = Column(Integer, ForeignKey("load_cases.id"), nullable=False)
    direction = Column(String(10), nullable=False)  # 'X' or 'Y'

    # Absolute maximum drift value
    absolute_max_drift = Column(Float, nullable=False)

    # Sign of the absolute maximum: 'positive' or 'negative'
    sign = Column(String(10), nullable=False)

    # Original Max and Min values for reference
    original_max = Column(Float, nullable=False)
    original_min = Column(Float, nullable=False)

    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)

    # Composite unique constraint
    __table_args__ = (
        Index("ix_absmaxmin_lookup", "project_id", "result_set_id", "story_id", "load_case_id", "direction", unique=True),
        Index("ix_absmaxmin_resultset", "result_set_id"),
    )

    def __repr__(self):
        return f"<AbsoluteMaxMinDrift(story_id={self.story_id}, load_case_id={self.load_case_id}, dir={self.direction}, abs_max={self.absolute_max_drift}, sign={self.sign})>"


class WallShear(Base):
    """Wall shear force results (element-level forces by story)."""

    __tablename__ = "wall_shears"

    id = Column(Integer, primary_key=True, autoincrement=True)
    element_id = Column(Integer, ForeignKey("elements.id"), nullable=False)
    story_id = Column(Integer, ForeignKey("stories.id"), nullable=False)
    load_case_id = Column(Integer, ForeignKey("load_cases.id"), nullable=False)
    result_category_id = Column(Integer, ForeignKey("result_categories.id"), nullable=True)
    direction = Column(String(10), nullable=False)  # 'V2' or 'V3'
    location = Column(String(20), nullable=True)  # 'Top' or 'Bottom' (only Bottom used for shears)
    force = Column(Float, nullable=False)
    max_force = Column(Float, nullable=True)
    min_force = Column(Float, nullable=True)
    story_sort_order = Column(Integer, nullable=True)  # Story order from Pier Forces sheet (per element)

    # Relationships
    element = relationship("Element", back_populates="wall_shears")
    story = relationship("Story")
    load_case = relationship("LoadCase", overlaps="wall_shears")
    result_category = relationship("ResultCategory", overlaps="wall_shears")

    # Indexes
    __table_args__ = (
        Index("ix_wallshear_element_story_case", "element_id", "story_id", "load_case_id", "direction"),
        Index("ix_wallshear_category", "result_category_id"),
    )

    def __repr__(self):
        return f"<WallShear(element_id={self.element_id}, story_id={self.story_id}, case={self.load_case_id}, dir={self.direction}, force={self.force})>"


class QuadRotation(Base):
    """Quad strain gauge rotation results (element-level rotations by story).

    Data from 'Quad Strain Gauge - Rotation' sheet.
    Rotations are stored in radians but displayed as percentages (multiplied by 100).
    """

    __tablename__ = "quad_rotations"

    id = Column(Integer, primary_key=True, autoincrement=True)
    element_id = Column(Integer, ForeignKey("elements.id"), nullable=False)
    story_id = Column(Integer, ForeignKey("stories.id"), nullable=False)
    load_case_id = Column(Integer, ForeignKey("load_cases.id"), nullable=False)
    result_category_id = Column(Integer, ForeignKey("result_categories.id"), nullable=True)
    quad_name = Column(String(50), nullable=True)  # Quad element identifier (from 'Name' column)
    direction = Column(String(20), nullable=True)  # Direction (typically 'Pier')
    rotation = Column(Float, nullable=False)  # Rotation in radians
    max_rotation = Column(Float, nullable=True)  # Max rotation in radians
    min_rotation = Column(Float, nullable=True)  # Min rotation in radians
    story_sort_order = Column(Integer, nullable=True)  # Story order from Quad Strain sheet (per element)

    # Relationships
    element = relationship("Element", back_populates="quad_rotations")
    story = relationship("Story")
    load_case = relationship("LoadCase", overlaps="quad_rotations")
    result_category = relationship("ResultCategory", overlaps="quad_rotations")

    # Indexes
    __table_args__ = (
        Index("ix_quadrot_element_story_case", "element_id", "story_id", "load_case_id"),
        Index("ix_quadrot_category", "result_category_id"),
    )

    def __repr__(self):
        return f"<QuadRotation(element={self.element_id}, story={self.story_id}, case={self.load_case_id}, rotation={self.rotation})>"


class ColumnShear(Base):
    """Column shear force results (element-level forces by story).

    Data from 'Element Forces - Columns' sheet.
    Similar to WallShear but for column elements.
    """

    __tablename__ = "column_shears"

    id = Column(Integer, primary_key=True, autoincrement=True)
    element_id = Column(Integer, ForeignKey("elements.id"), nullable=False)
    story_id = Column(Integer, ForeignKey("stories.id"), nullable=False)
    load_case_id = Column(Integer, ForeignKey("load_cases.id"), nullable=False)
    result_category_id = Column(Integer, ForeignKey("result_categories.id"), nullable=True)
    direction = Column(String(10), nullable=False)  # 'V2' or 'V3'
    location = Column(String(20), nullable=True)  # 'Top' or 'Bottom' (typically use both for columns)
    force = Column(Float, nullable=False)
    max_force = Column(Float, nullable=True)
    min_force = Column(Float, nullable=True)
    story_sort_order = Column(Integer, nullable=True)  # Story order from Column Forces sheet (per element)

    # Relationships
    element = relationship("Element", overlaps="column_shears")
    story = relationship("Story")
    load_case = relationship("LoadCase", overlaps="column_shears")
    result_category = relationship("ResultCategory", overlaps="column_shears")

    # Indexes
    __table_args__ = (
        Index("ix_colshear_element_story_case", "element_id", "story_id", "load_case_id", "direction"),
        Index("ix_colshear_category", "result_category_id"),
    )

    def __repr__(self):
        return f"<ColumnShear(element_id={self.element_id}, story_id={self.story_id}, case={self.load_case_id}, dir={self.direction}, force={self.force})>"


class ColumnAxial(Base):
    """Column minimum axial force results (element-level compression forces by story).

    Data from 'Element Forces - Columns' sheet.
    Stores minimum (most compression) P values for each column at each story.
    """

    __tablename__ = "column_axials"

    id = Column(Integer, primary_key=True, autoincrement=True)
    element_id = Column(Integer, ForeignKey("elements.id"), nullable=False)
    story_id = Column(Integer, ForeignKey("stories.id"), nullable=False)
    load_case_id = Column(Integer, ForeignKey("load_cases.id"), nullable=False)
    result_category_id = Column(Integer, ForeignKey("result_categories.id"), nullable=True)
    location = Column(String(20), nullable=True)  # 'Top' or 'Bottom'
    min_axial = Column(Float, nullable=False)  # Minimum (most compression) P value
    story_sort_order = Column(Integer, nullable=True)  # Story order from Column Forces sheet (per element)

    # Relationships
    element = relationship("Element", overlaps="column_axials")
    story = relationship("Story")
    load_case = relationship("LoadCase", overlaps="column_axials")
    result_category = relationship("ResultCategory", overlaps="column_axials")

    # Indexes
    __table_args__ = (
        Index("ix_colaxial_element_story_case", "element_id", "story_id", "load_case_id"),
        Index("ix_colaxial_category", "result_category_id"),
    )

    def __repr__(self):
        return f"<ColumnAxial(element_id={self.element_id}, story_id={self.story_id}, case={self.load_case_id}, min_axial={self.min_axial})>"


class ColumnRotation(Base):
    """Column rotation results from fiber hinge states (element-level rotations by story).

    Data from 'Fiber Hinge States' sheet.
    Rotations R2 and R3 are stored in radians but displayed as percentages (multiplied by 100).
    Only processes columns (Frame/Wall starts with 'C').
    """

    __tablename__ = "column_rotations"

    id = Column(Integer, primary_key=True, autoincrement=True)
    element_id = Column(Integer, ForeignKey("elements.id"), nullable=False)
    story_id = Column(Integer, ForeignKey("stories.id"), nullable=False)
    load_case_id = Column(Integer, ForeignKey("load_cases.id"), nullable=False)
    result_category_id = Column(Integer, ForeignKey("result_categories.id"), nullable=True)
    direction = Column(String(10), nullable=False)  # 'R2' or 'R3'
    rotation = Column(Float, nullable=False)  # Rotation in radians
    max_rotation = Column(Float, nullable=True)  # Max rotation in radians
    min_rotation = Column(Float, nullable=True)  # Min rotation in radians
    story_sort_order = Column(Integer, nullable=True)  # Story order from Fiber Hinge States sheet (per element)

    # Relationships
    element = relationship("Element", overlaps="column_rotations")
    story = relationship("Story")
    load_case = relationship("LoadCase", overlaps="column_rotations")
    result_category = relationship("ResultCategory", overlaps="column_rotations")

    # Indexes
    __table_args__ = (
        Index("ix_colrot_element_story_case", "element_id", "story_id", "load_case_id", "direction"),
        Index("ix_colrot_category", "result_category_id"),
    )

    def __repr__(self):
        return f"<ColumnRotation(element_id={self.element_id}, story_id={self.story_id}, case={self.load_case_id}, dir={self.direction}, rotation={self.rotation})>"


class BeamRotation(Base):
    """Beam rotation results from hinge states (element-level R3 plastic rotations by story).

    Data from 'Hinge States' sheet.
    R3 Plastic rotations are stored in radians but displayed as percentages (multiplied by 100).
    Only processes beams (Frame/Wall starts with 'B').
    """
    __tablename__ = "beam_rotations"

    id = Column(Integer, primary_key=True, autoincrement=True)
    element_id = Column(Integer, ForeignKey("elements.id"), nullable=False)
    story_id = Column(Integer, ForeignKey("stories.id"), nullable=False)
    load_case_id = Column(Integer, ForeignKey("load_cases.id"), nullable=False)
    result_category_id = Column(Integer, ForeignKey("result_categories.id"), nullable=True)
    hinge = Column(String(20), nullable=True)  # Hinge identifier (e.g., "SB2")
    generated_hinge = Column(String(20), nullable=True)  # Generated hinge ID (e.g., "B19H1")
    rel_dist = Column(Float, nullable=True)  # Relative distance
    r3_plastic = Column(Float, nullable=False)  # R3 Plastic rotation in radians
    max_r3_plastic = Column(Float, nullable=True)  # Max R3 rotation in radians
    min_r3_plastic = Column(Float, nullable=True)  # Min R3 rotation in radians
    story_sort_order = Column(Integer, nullable=True)  # Story order from Hinge States sheet (per element)

    # Relationships
    element = relationship("Element", overlaps="beam_rotations")
    story = relationship("Story")
    load_case = relationship("LoadCase", overlaps="beam_rotations")
    result_category = relationship("ResultCategory", overlaps="beam_rotations")

    # Indexes
    __table_args__ = (
        Index("ix_beamrot_element_story_case", "element_id", "story_id", "load_case_id"),
        Index("ix_beamrot_category", "result_category_id"),
    )

    def __repr__(self):
        return f"<BeamRotation(element_id={self.element_id}, story_id={self.story_id}, case={self.load_case_id}, r3_plastic={self.r3_plastic})>"


class SoilPressure(Base):
    """Soil pressure results at foundation joints (joint-level minimum pressures).

    Data from 'Soil Pressures' sheet.
    Stores minimum soil pressure per unique shell element (foundation element).
    Each unique name represents a foundation element with multiple joints.
    """

    __tablename__ = "soil_pressures"

    id = Column(Integer, primary_key=True, autoincrement=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    result_set_id = Column(Integer, ForeignKey("result_sets.id"), nullable=True)
    result_category_id = Column(Integer, ForeignKey("result_categories.id"), nullable=True)
    load_case_id = Column(Integer, ForeignKey("load_cases.id"), nullable=False)

    # Foundation element identification
    shell_object = Column(String(50), nullable=False)  # Shell object name (e.g., "F27")
    unique_name = Column(String(50), nullable=False)  # Unique element ID (e.g., "72")

    # Soil pressure value (minimum across all joints for this element)
    min_pressure = Column(Float, nullable=False)  # kN/m²

    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    project = relationship("Project")
    load_case = relationship("LoadCase")
    result_category = relationship("ResultCategory")

    # Indexes
    __table_args__ = (
        Index("ix_soilpressure_project_resultset", "project_id", "result_set_id"),
        Index("ix_soilpressure_loadcase", "load_case_id"),
        Index("ix_soilpressure_unique", "project_id", "result_set_id", "unique_name", "load_case_id", unique=True),
    )

    def __repr__(self):
        return f"<SoilPressure(shell_obj='{self.shell_object}', unique='{self.unique_name}', case={self.load_case_id}, pressure={self.min_pressure})>"


class VerticalDisplacement(Base):
    """Vertical displacement results at foundation joints (joint-level min displacements).

    Data from 'Joint Displacements' sheet, filtered by joints specified in 'Fou' sheet.
    Stores minimum vertical (Uz) displacement per joint across Max/Min steps.
    Each unique name represents a specific joint at a foundation location.
    """

    __tablename__ = "vertical_displacements"

    id = Column(Integer, primary_key=True, autoincrement=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    result_set_id = Column(Integer, ForeignKey("result_sets.id"), nullable=True)
    result_category_id = Column(Integer, ForeignKey("result_categories.id"), nullable=True)
    load_case_id = Column(Integer, ForeignKey("load_cases.id"), nullable=False)

    # Joint identification
    story = Column(String(20), nullable=False)  # Story name (e.g., "L10")
    label = Column(String(50), nullable=False)  # Joint label
    unique_name = Column(String(50), nullable=False)  # Unique joint ID (from Fou sheet)

    # Vertical displacement value (minimum Uz)
    min_displacement = Column(Float, nullable=False)  # mm

    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    project = relationship("Project")
    load_case = relationship("LoadCase")
    result_category = relationship("ResultCategory")

    # Indexes
    __table_args__ = (
        Index("ix_vertdisp_project_resultset", "project_id", "result_set_id"),
        Index("ix_vertdisp_loadcase", "load_case_id"),
        Index("ix_vertdisp_unique", "project_id", "result_set_id", "unique_name", "load_case_id", unique=True),
    )

    def __repr__(self):
        return f"<VerticalDisplacement(story='{self.story}', unique='{self.unique_name}', case={self.load_case_id}, disp={self.min_displacement})>"


class ElementResultsCache(Base):
    """Wide-format cache for element-level results optimized for tabular display.

    One row per (element, story), with all load cases stored as JSON for fast retrieval.
    Similar to GlobalResultsCache but scoped to individual structural elements.
    Format: {"TH01": 123.4, "TH02": 145.6, ...}
    """

    __tablename__ = "element_results_cache"

    id = Column(Integer, primary_key=True, autoincrement=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    result_set_id = Column(Integer, ForeignKey("result_sets.id"), nullable=True)
    result_type = Column(String(50), nullable=False)  # 'WallShears_V22', 'WallShears_V33', etc.
    element_id = Column(Integer, ForeignKey("elements.id"), nullable=False)
    story_id = Column(Integer, ForeignKey("stories.id"), nullable=False)

    # Wide-format data stored as JSON
    results_matrix = Column(JSON, nullable=False)

    # Story ordering from source sheet (per-element ordering for structural elements)
    story_sort_order = Column(Integer, nullable=True)

    # Metadata
    last_updated = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    result_set = relationship("ResultSet")

    # Composite index for fast lookups
    __table_args__ = (
        Index("ix_elem_cache_lookup", "project_id", "result_set_id", "result_type", "element_id"),
        Index("ix_elem_cache_element", "element_id"),
        Index("ix_elem_cache_story", "story_id"),
    )

    def __repr__(self):
        return f"<ElementResultsCache(project_id={self.project_id}, type='{self.result_type}', element_id={self.element_id}, story_id={self.story_id})>"


class JointResultsCache(Base):
    """Wide-format cache for joint-level results optimized for tabular display.

    One row per foundation element (unique shell), with all load cases stored as JSON.
    Used for soil pressures and other joint-based results.
    Format: {"TH01": -450.2, "TH02": -380.5, ...}
    """

    __tablename__ = "joint_results_cache"

    id = Column(Integer, primary_key=True, autoincrement=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    result_set_id = Column(Integer, ForeignKey("result_sets.id"), nullable=True)
    result_type = Column(String(50), nullable=False)  # 'SoilPressures_Min'

    # Foundation element identification
    shell_object = Column(String(50), nullable=False)
    unique_name = Column(String(50), nullable=False)

    # Wide-format data stored as JSON
    results_matrix = Column(JSON, nullable=False)

    # Metadata
    last_updated = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    result_set = relationship("ResultSet")

    # Composite index for fast lookups
    __table_args__ = (
        Index("ix_joint_cache_lookup", "project_id", "result_set_id", "result_type"),
        Index("ix_joint_cache_unique", "project_id", "result_set_id", "result_type", "unique_name", unique=True),
    )

    def __repr__(self):
        return f"<JointResultsCache(project_id={self.project_id}, type='{self.result_type}', unique='{self.unique_name}')>"


class PushoverCase(Base):
    """Represents a pushover load case (e.g., Push_Mod_X+Ecc+, Push_Mod_Y-Ecc-)."""

    __tablename__ = "pushover_cases"

    id = Column(Integer, primary_key=True, autoincrement=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    result_set_id = Column(Integer, ForeignKey("result_sets.id"), nullable=True)
    name = Column(String(100), nullable=False)  # 'Push_Mod_X+Ecc+', etc.
    direction = Column(String(10), nullable=False)  # 'X' or 'Y'
    base_story = Column(String(100), nullable=True)  # Base story for shear extraction
    description = Column(Text, nullable=True)

    # Relationships
    project = relationship("Project", backref="pushover_cases")
    result_set = relationship("ResultSet")
    curve_points = relationship("PushoverCurvePoint", back_populates="pushover_case", cascade="all, delete-orphan")

    # Composite unique constraint
    __table_args__ = (Index("ix_project_pushover_case", "project_id", "result_set_id", "name", unique=True),)

    def __repr__(self):
        return f"<PushoverCase(id={self.id}, name='{self.name}', direction='{self.direction}')>"


class PushoverCurvePoint(Base):
    """Individual data point on a pushover curve (displacement vs base shear)."""

    __tablename__ = "pushover_curve_points"

    id = Column(Integer, primary_key=True, autoincrement=True)
    pushover_case_id = Column(Integer, ForeignKey("pushover_cases.id"), nullable=False)
    step_number = Column(Integer, nullable=False)
    displacement = Column(Float, nullable=False)  # Roof displacement (mm)
    base_shear = Column(Float, nullable=False)  # Base shear force (kN)

    # Relationships
    pushover_case = relationship("PushoverCase", back_populates="curve_points")

    # Index for ordering points by step
    __table_args__ = (
        Index("ix_curve_case_step", "pushover_case_id", "step_number"),
    )

    def __repr__(self):
        return f"<PushoverCurvePoint(case={self.pushover_case_id}, step={self.step_number}, disp={self.displacement}, shear={self.base_shear})>"
