"""Joint-level result models: SoilPressure, VerticalDisplacement."""

from sqlalchemy import (
    Column,
    Integer,
    String,
    Float,
    DateTime,
    ForeignKey,
    Index,
)
from sqlalchemy.orm import relationship
from datetime import datetime

from ..base import Base


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
    min_pressure = Column(Float, nullable=False)  # kN/m2

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
