"""Element-level result models: WallShear, QuadRotation, ColumnShear, ColumnAxial, ColumnRotation, BeamRotation."""

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
    """Column axial force results (element-level compression/tension forces by story).

    Data from 'Element Forces - Columns' sheet.
    Stores both minimum (most compression) and maximum (most tension) P values.
    """

    __tablename__ = "column_axials"

    id = Column(Integer, primary_key=True, autoincrement=True)
    element_id = Column(Integer, ForeignKey("elements.id"), nullable=False)
    story_id = Column(Integer, ForeignKey("stories.id"), nullable=False)
    load_case_id = Column(Integer, ForeignKey("load_cases.id"), nullable=False)
    result_category_id = Column(Integer, ForeignKey("result_categories.id"), nullable=True)
    location = Column(String(20), nullable=True)  # 'Top' or 'Bottom'
    min_axial = Column(Float, nullable=False)  # Minimum (most compression) P value
    max_axial = Column(Float, nullable=True)  # Maximum (most tension) P value
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
    step_type = Column(String(10), nullable=True)  # Step type (e.g., "Max", "Min")
    hinge = Column(String(20), nullable=True)  # Hinge identifier (e.g., "SB2")
    generated_hinge = Column(String(20), nullable=True)  # Generated hinge ID (e.g., "B19H1")
    rel_dist = Column(Float, nullable=True)  # Relative distance
    r3_plastic = Column(Float, nullable=False)  # R3 Plastic rotation in radians
    max_r3_plastic = Column(Float, nullable=True)  # Max R3 rotation in radians
    min_r3_plastic = Column(Float, nullable=True)  # Min R3 rotation in radians
    story_sort_order = Column(Integer, nullable=True)  # Source row order from Hinge States sheet

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
