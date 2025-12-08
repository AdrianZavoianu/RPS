"""Results tree browser - re-exports from gui.tree_browser package.

This module provides backward compatibility. New code should import directly
from gui.tree_browser.
"""

# Re-export for backward compatibility
from .tree_browser import ResultsTreeBrowser

__all__ = ["ResultsTreeBrowser"]
