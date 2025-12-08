"""Project detail window - re-exports from gui.project_detail package.

This module provides backward compatibility. New code should import directly
from gui.project_detail.
"""

# Re-export for backward compatibility
from .project_detail import ProjectDetailWindow

__all__ = ["ProjectDetailWindow"]
