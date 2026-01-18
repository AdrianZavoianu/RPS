"""Pushover analysis models: PushoverCase, PushoverCurvePoint."""

from sqlalchemy import (
    Column,
    Integer,
    String,
    Float,
    ForeignKey,
    Text,
    Index,
)
from sqlalchemy.orm import relationship

from ..base import Base


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
