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
    direction = Column(String(10), nullable=False)  # 'X' or 'Y'
    drift = Column(Float, nullable=False)
    max_drift = Column(Float, nullable=True)  # Maximum across all points
    min_drift = Column(Float, nullable=True)  # Minimum across all points

    # Relationships
    story = relationship("Story", back_populates="drifts")
    load_case = relationship("LoadCase", back_populates="story_drifts")

    # Indexes for fast querying
    __table_args__ = (
        Index("ix_drift_story_case", "story_id", "load_case_id", "direction"),
    )

    def __repr__(self):
        return f"<StoryDrift(story_id={self.story_id}, case={self.load_case_id}, dir={self.direction}, drift={self.drift})>"


class StoryAcceleration(Base):
    """Story acceleration results."""

    __tablename__ = "story_accelerations"

    id = Column(Integer, primary_key=True, autoincrement=True)
    story_id = Column(Integer, ForeignKey("stories.id"), nullable=False)
    load_case_id = Column(Integer, ForeignKey("load_cases.id"), nullable=False)
    direction = Column(String(10), nullable=False)  # 'UX' or 'UY'
    acceleration = Column(Float, nullable=False)  # In g units
    max_acceleration = Column(Float, nullable=True)
    min_acceleration = Column(Float, nullable=True)

    # Relationships
    story = relationship("Story", back_populates="accelerations")
    load_case = relationship("LoadCase", back_populates="story_accelerations")

    # Indexes
    __table_args__ = (
        Index("ix_accel_story_case", "story_id", "load_case_id", "direction"),
    )

    def __repr__(self):
        return f"<StoryAcceleration(story_id={self.story_id}, case={self.load_case_id}, accel={self.acceleration}g)>"


class StoryForce(Base):
    """Story shear force results."""

    __tablename__ = "story_forces"

    id = Column(Integer, primary_key=True, autoincrement=True)
    story_id = Column(Integer, ForeignKey("stories.id"), nullable=False)
    load_case_id = Column(Integer, ForeignKey("load_cases.id"), nullable=False)
    direction = Column(String(10), nullable=False)  # 'VX' or 'VY'
    location = Column(String(20), nullable=True)  # 'Top' or 'Bottom'
    force = Column(Float, nullable=False)
    max_force = Column(Float, nullable=True)
    min_force = Column(Float, nullable=True)

    # Relationships
    story = relationship("Story", back_populates="forces")
    load_case = relationship("LoadCase", back_populates="story_forces")

    # Indexes
    __table_args__ = (
        Index("ix_force_story_case", "story_id", "load_case_id", "direction"),
    )

    def __repr__(self):
        return f"<StoryForce(story_id={self.story_id}, case={self.load_case_id}, force={self.force})>"


# Additional models for future expansion

class Element(Base):
    """Base table for structural elements (columns, beams, piers, etc.)."""

    __tablename__ = "elements"

    id = Column(Integer, primary_key=True, autoincrement=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    element_type = Column(String(50), nullable=False)  # 'Column', 'Beam', 'Pier', 'Link'
    name = Column(String(100), nullable=False)
    unique_name = Column(String(100), nullable=True)  # From ETABS/SAP2000
    story_id = Column(Integer, ForeignKey("stories.id"), nullable=True)

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
    name = Column(String(100), nullable=False)  # 'DES', 'MCE', etc.
    result_category = Column(String(50), nullable=True)  # 'Envelopes', 'Time-Series'
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    project = relationship("Project", back_populates="result_sets")
    cache_entries = relationship("GlobalResultsCache", back_populates="result_set", cascade="all, delete-orphan")

    # Composite unique constraint
    __table_args__ = (Index("ix_project_resultset", "project_id", "name", unique=True),)

    def __repr__(self):
        return f"<ResultSet(id={self.id}, name='{self.name}', category='{self.result_category}')>"


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
