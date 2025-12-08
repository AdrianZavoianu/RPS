"""Repository pattern for database access - provides clean interface to database operations.

This module re-exports all repositories from the repositories package for backward compatibility.
New code should import directly from database.repositories.
"""

# Re-export all repositories for backward compatibility
from .repositories import (
    # Project
    ProjectRepository,
    # Load Case
    LoadCaseRepository,
    # Story
    StoryRepository,
    StoryDriftDataRepository,
    StoryAccelerationDataRepository,
    StoryForceDataRepository,
    StoryDisplacementDataRepository,
    ResultRepository,
    # Result Set
    ResultSetRepository,
    ComparisonSetRepository,
    # Element
    ElementRepository,
    # Cache
    CacheRepository,
    ElementCacheRepository,
    JointCacheRepository,
    AbsoluteMaxMinDriftRepository,
    ResultCategoryRepository,
    # Foundation
    SoilPressureRepository,
    VerticalDisplacementRepository,
    # Pushover
    PushoverCaseRepository,
)

__all__ = [
    # Project
    "ProjectRepository",
    # Load Case
    "LoadCaseRepository",
    # Story
    "StoryRepository",
    "StoryDriftDataRepository",
    "StoryAccelerationDataRepository",
    "StoryForceDataRepository",
    "StoryDisplacementDataRepository",
    "ResultRepository",
    # Result Set
    "ResultSetRepository",
    "ComparisonSetRepository",
    # Element
    "ElementRepository",
    # Cache
    "CacheRepository",
    "ElementCacheRepository",
    "JointCacheRepository",
    "AbsoluteMaxMinDriftRepository",
    "ResultCategoryRepository",
    # Foundation
    "SoilPressureRepository",
    "VerticalDisplacementRepository",
    # Pushover
    "PushoverCaseRepository",
]
