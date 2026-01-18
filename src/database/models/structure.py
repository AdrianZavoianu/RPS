"""Structural element models: Element, TimeHistoryData."""

from sqlalchemy import (
    Column,
    Integer,
    String,
    Float,
    ForeignKey,
    Index,
)
from sqlalchemy.orm import relationship

from ..base import Base


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
