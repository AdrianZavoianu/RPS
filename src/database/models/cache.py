"""Cache models: GlobalResultsCache, ElementResultsCache, JointResultsCache, TimeSeriesGlobalCache, AbsoluteMaxMinDrift."""

from sqlalchemy import (
    Column,
    Integer,
    String,
    Float,
    DateTime,
    ForeignKey,
    Index,
    JSON,
)
from sqlalchemy.orm import relationship
from datetime import datetime

from ..base import Base


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
        Index("ix_cache_lookup_project_type", "project_id", "result_type"),
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
        Index("ix_elem_cache_project_type", "project_id", "result_type"),
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
        Index("ix_joint_cache_project_type", "project_id", "result_type"),
        Index("ix_joint_cache_unique", "project_id", "result_set_id", "result_type", "unique_name", unique=True),
    )

    def __repr__(self):
        return f"<JointResultsCache(project_id={self.project_id}, type='{self.result_type}', unique='{self.unique_name}')>"


class TimeSeriesGlobalCache(Base):
    """Cache for time-history global results optimized for animated visualization.

    Stores per-story time series data as JSON arrays for efficient retrieval and animation.
    Each row contains all time steps for a single story/direction combination.
    Format: {
        "time_steps": [0.0, 0.01, 0.02, ...],
        "values": [0.0012, 0.0015, 0.0018, ...]
    }
    """

    __tablename__ = "time_series_global_cache"

    id = Column(Integer, primary_key=True, autoincrement=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    result_set_id = Column(Integer, ForeignKey("result_sets.id"), nullable=False)
    load_case_name = Column(String(100), nullable=False)  # e.g., 'TH02'
    result_type = Column(String(50), nullable=False)  # 'Drifts', 'Displacements', 'Forces', 'Accelerations'
    direction = Column(String(10), nullable=False)  # 'X' or 'Y'
    story_id = Column(Integer, ForeignKey("stories.id"), nullable=False)

    # Time series data stored as JSON
    time_steps = Column(JSON, nullable=False)  # Array of time values [0.0, 0.01, 0.02, ...]
    values = Column(JSON, nullable=False)  # Array of result values corresponding to time_steps

    # Story ordering for building profile display
    story_sort_order = Column(Integer, nullable=True)

    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    result_set = relationship("ResultSet")
    story = relationship("Story")

    # Composite indexes for fast lookups
    __table_args__ = (
        Index("ix_ts_global_lookup", "project_id", "result_set_id", "load_case_name", "result_type", "direction"),
        Index("ix_ts_global_story", "story_id"),
        Index("ix_ts_global_unique", "project_id", "result_set_id", "load_case_name", "result_type", "direction", "story_id", unique=True),
    )

    def __repr__(self):
        return f"<TimeSeriesGlobalCache(result_set={self.result_set_id}, case='{self.load_case_name}', type='{self.result_type}', dir='{self.direction}', story={self.story_id})>"
