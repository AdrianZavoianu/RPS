"""Tree browser package for hierarchical result navigation.

This package provides the ResultsTreeBrowser widget and supporting modules:
- browser: Main ResultsTreeBrowser class
- nltha_builders: NLTHA section tree builders
- pushover_builders: Pushover section tree builders
- comparison_builders: Comparison set tree builders
- click_handlers: Item click event handlers
"""

from .browser import ResultsTreeBrowser

__all__ = ["ResultsTreeBrowser"]
