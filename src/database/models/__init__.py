"""Database models package.

Re-exports all models from submodules for backward compatibility.
New code can import directly from submodules for better organization.
"""

# Base class
from ..base import Base

# Core models
from .core import Project, LoadCase, Story

# Global results
from .global_results import (
    StoryDrift,
    StoryAcceleration,
    StoryForce,
    StoryDisplacement,
)

# Structural elements
from .structure import Element, TimeHistoryData

# Result sets and categories
from .result_sets import ResultSet, ComparisonSet, ResultCategory

# Element-level results
from .element_results import (
    WallShear,
    QuadRotation,
    ColumnShear,
    ColumnAxial,
    ColumnRotation,
    BeamRotation,
)

# Joint-level results
from .joint_results import SoilPressure, VerticalDisplacement

# Cache tables
from .cache import (
    GlobalResultsCache,
    AbsoluteMaxMinDrift,
    ElementResultsCache,
    JointResultsCache,
    TimeSeriesGlobalCache,
)

# Pushover models
from .pushover import PushoverCase, PushoverCurvePoint

__all__ = [
    # Base
    "Base",
    # Core
    "Project",
    "LoadCase",
    "Story",
    # Global results
    "StoryDrift",
    "StoryAcceleration",
    "StoryForce",
    "StoryDisplacement",
    # Structure
    "Element",
    "TimeHistoryData",
    # Result sets
    "ResultSet",
    "ComparisonSet",
    "ResultCategory",
    # Element results
    "WallShear",
    "QuadRotation",
    "ColumnShear",
    "ColumnAxial",
    "ColumnRotation",
    "BeamRotation",
    # Joint results
    "SoilPressure",
    "VerticalDisplacement",
    # Cache
    "GlobalResultsCache",
    "AbsoluteMaxMinDrift",
    "ElementResultsCache",
    "JointResultsCache",
    "TimeSeriesGlobalCache",
    # Pushover
    "PushoverCase",
    "PushoverCurvePoint",
]
