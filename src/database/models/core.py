"""Core database models: Project, LoadCase, Story."""

from sqlalchemy import (
    Column,
    Integer,
    String,
    Float,
    DateTime,
    ForeignKey,
    Text,
    Index,
)
from sqlalchemy.orm import relationship
from datetime import datetime

from ..base import Base


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
