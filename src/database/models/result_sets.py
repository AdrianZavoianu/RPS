"""Result set models: ResultSet, ComparisonSet, ResultCategory."""

from sqlalchemy import (
    Column,
    Integer,
    String,
    DateTime,
    ForeignKey,
    Text,
    Index,
    JSON,
)
from sqlalchemy.orm import relationship
from datetime import datetime

from ..base import Base


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
    """Represents a category within a result set (Envelopes/Time-Series -> Global/Elements/Joints)."""

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
