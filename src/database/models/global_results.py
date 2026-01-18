"""Global/story-level result models: StoryDrift, StoryAcceleration, StoryForce, StoryDisplacement."""

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
