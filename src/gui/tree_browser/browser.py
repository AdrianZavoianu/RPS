"""Results tree browser - hierarchical navigation for project results.

This is the main browser class that delegates to specialized builder modules
for constructing tree sections.
"""

import logging

from PyQt6.QtCore import Qt, pyqtSignal, QTimer
from PyQt6.QtWidgets import QTreeWidget, QTreeWidgetItem, QVBoxLayout, QWidget, QHBoxLayout, QLabel
from PyQt6.QtGui import QPainter, QLinearGradient, QColor
from gui.ui_helpers import create_styled_label

from . import click_handlers
from . import comparison_builders
from . import nltha_builders
from . import pushover_builders

logger = logging.getLogger(__name__)


class ResultsTreeBrowser(QWidget):
    """Tree browser for navigating project results."""

    selection_changed = pyqtSignal(int, str, str, str, int)  # (result_set_id, category, result_type, direction, element_id)
    comparison_selected = pyqtSignal(int, str, str)  # (comparison_set_id, result_type, direction)
    comparison_element_selected = pyqtSignal(int, str, int, str)  # (comparison_set_id, result_type, element_id, direction)

    def __init__(self, project_id: int, parent=None):
        super().__init__(parent)
        self.project_id = project_id
        self.elements = []  # Will be populated with project elements
        self.available_result_types = {}
        self.comparison_sets = []
        self.pushover_cases = {}
        self.time_series_load_cases = {}  # Dict[result_set_id, List[str]] of load case names
        self.setup_ui()

    def _has_data_for(self, result_set_id: int, result_type: str) -> bool:
        """Check if data exists for a given result type in a result set."""
        if not self.available_result_types:
            return True  # If no info provided, show all (backward compatibility)

        result_types_for_set = self.available_result_types.get(result_set_id, set())

        # If no info for this result set, show all (backward compatibility)
        if not result_types_for_set:
            return True

        return result_type in result_types_for_set

    def _has_time_series_data(self, result_set_id: int) -> bool:
        """Check if time series data exists for a result set."""
        if not self.available_result_types:
            return False  # No data loaded yet

        result_types_for_set = self.available_result_types.get(result_set_id, set())

        # Check for TimeSeriesGlobal marker in result types
        return "TimeSeriesGlobal" in result_types_for_set

    def setup_ui(self):
        """Setup the browser UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Browser header with title aligned with content title
        browser_header = QWidget()
        browser_header.setFixedHeight(32)
        browser_header_layout = QHBoxLayout(browser_header)
        browser_header_layout.setContentsMargins(4, 2, 4, 2)
        browser_header_layout.setSpacing(8)

        # Browser title - secondary in hierarchy, with left margin
        self.browser_title = QLabel("Results")
        self.browser_title.setStyleSheet("""
            font-size: 16px;
            font-weight: 600;
            color: #d1d5db;
            padding-left: 8px;
        """)
        browser_header_layout.addWidget(self.browser_title)
        browser_header_layout.addStretch()

        layout.addWidget(browser_header, stretch=0)

        # Add spacing after header
        layout.addSpacing(4)

        # Wrap tree in container with fade indicators
        tree_container = QWidget()
        tree_container_layout = QVBoxLayout(tree_container)
        tree_container_layout.setContentsMargins(0, 0, 0, 0)
        tree_container_layout.setSpacing(0)

        # Tree widget
        self.tree = QTreeWidget()
        self.tree.setHeaderHidden(True)
        self.tree.setIndentation(6)  # Compact indentation
        self.tree.setAnimated(True)
        self.tree.setUniformRowHeights(False)
        self.tree.itemClicked.connect(self.on_item_clicked)
        self.tree.itemExpanded.connect(self._on_item_expanded)

        # Connect scroll events to update fade indicators
        self.tree.verticalScrollBar().valueChanged.connect(self._update_fade_indicators)
        self.tree.verticalScrollBar().rangeChanged.connect(self._update_fade_indicators)

        # Ultra-minimal scrollbar styling - only 2px, very transparent, auto-hide
        self.tree.setStyleSheet("""
            QTreeWidget {
                background-color: transparent;
                border: none;
                outline: none;
                padding: 0px;
                font-size: 14px;
            }
            QTreeWidget QScrollBar:vertical {
                background-color: transparent;
                width: 2px;
                border: none;
                margin: 0px;
            }
            QTreeWidget QScrollBar::handle:vertical {
                background-color: rgba(255, 255, 255, 0.03);
                border-radius: 1px;
                min-height: 20px;
            }
            QTreeWidget QScrollBar::handle:vertical:hover {
                background-color: rgba(255, 255, 255, 0.08);
            }
            QTreeWidget QScrollBar::add-line:vertical, QTreeWidget QScrollBar::sub-line:vertical {
                height: 0px;
            }
            QTreeWidget QScrollBar::add-page:vertical, QTreeWidget QScrollBar::sub-page:vertical {
                background: none;
            }
            QTreeWidget::item {
                padding: 4px 4px;
                border-radius: 2px;
                color: #9ca3af;
                margin: 1px 0px;
                border: none;
                background-color: transparent;
            }
            QTreeWidget::item:hover {
                background-color: rgba(255, 255, 255, 0.03);
                color: #d1d5db;
            }
            QTreeWidget::item:selected {
                background-color: rgba(74, 125, 137, 0.12);
                color: #67e8f9;
                font-weight: 400;
            }
            QTreeWidget::item:selected:hover {
                background-color: rgba(74, 125, 137, 0.18);
            }
            QTreeWidget::branch {
                background-color: transparent;
                border: none;
            }
            QTreeWidget::branch:has-children:closed {
                image: none;
                border: none;
            }
            QTreeWidget::branch:has-children:open {
                image: none;
                border: none;
            }
        """)

        tree_container_layout.addWidget(self.tree)
        
        layout.addWidget(tree_container)
        
        # Fade indicators overlay widget (parented to tree_container to position correctly)
        self.fade_overlay = _FadeIndicatorOverlay(tree_container, self.tree)
        self.fade_overlay.raise_()  # Ensure overlay is on top
        
        # Update fade indicators after layout and when tree is populated
        QTimer.singleShot(100, self._update_fade_indicators)
    
    def _update_fade_indicators(self):
        """Update fade indicators based on scroll position."""
        if hasattr(self, 'fade_overlay'):
            self.fade_overlay.update_indicators()

    def populate_tree(self, result_sets, stories, elements=None, available_result_types=None, comparison_sets=None, pushover_cases=None, time_series_load_cases=None):
        """Populate tree with project structure.

        Args:
            result_sets: List of ResultSet model instances
            stories: List of Story model instances
            elements: List of Element model instances (optional)
            available_result_types: Dict mapping result_set_id to set of available result types (optional)
            comparison_sets: List of ComparisonSet model instances (optional)
            pushover_cases: Dict mapping result_set_id to list of PushoverCase instances (optional)
            time_series_load_cases: Dict mapping result_set_id to list of load case names (optional)
        """
        self.tree.clear()

        # Update fade indicators after populating
        QTimer.singleShot(50, self._update_fade_indicators)
        self.elements = elements or []
        self.available_result_types = available_result_types or {}
        self.comparison_sets = comparison_sets or []
        self.pushover_cases = pushover_cases or {}
        self.time_series_load_cases = time_series_load_cases or {}

        if not result_sets and not self.comparison_sets:
            # Show empty state at top level
            placeholder = QTreeWidgetItem(self.tree)
            placeholder.setText(0, "No result sets")
            placeholder.setFlags(Qt.ItemFlag.NoItemFlags)
        else:
            # Separate result sets by analysis type
            nltha_sets = [rs for rs in result_sets if getattr(rs, 'analysis_type', 'NLTHA') == 'NLTHA']
            pushover_sets = [rs for rs in result_sets if getattr(rs, 'analysis_type', 'NLTHA') == 'Pushover']

            # NLTHA section (top-level, if any NLTHA result sets exist)
            if nltha_sets:
                nltha_root = QTreeWidgetItem(self.tree)
                nltha_root.setText(0, "◆ NLTHA")
                nltha_root.setData(0, Qt.ItemDataRole.UserRole, {"type": "analysis_section", "analysis_type": "NLTHA"})
                nltha_root.setExpanded(True)

                # Only expand first result set, rest collapsed
                for idx, result_set in enumerate(nltha_sets):
                    is_first = (idx == 0)
                    # Get the child count before adding to track which item we're adding
                    child_count_before = nltha_root.childCount()
                    nltha_builders.add_result_set(self, nltha_root, result_set, expand_first_path=is_first)
                    # Explicitly collapse non-first result sets
                    if not is_first:
                        result_set_item = nltha_root.child(child_count_before)
                        if result_set_item:
                            result_set_item.setExpanded(False)
                            # Also collapse all children of non-first result sets
                            for i in range(result_set_item.childCount()):
                                result_set_item.child(i).setExpanded(False)

                # Add comparison sets under NLTHA (collapsed by default)
                for comparison_set in self.comparison_sets:
                    comparison_builders.add_comparison_set(
                        nltha_root,
                        comparison_set,
                        self.elements,
                    )

            # Pushover section (top-level, if any pushover result sets exist)
            # Collapse Pushover if NLTHA exists (since NLTHA comes first)
            if pushover_sets:
                pushover_root = QTreeWidgetItem(self.tree)
                pushover_root.setText(0, "◆ Pushover")
                pushover_root.setData(0, Qt.ItemDataRole.UserRole, {"type": "analysis_section", "analysis_type": "Pushover"})
                # Only expand Pushover if there are no NLTHA sets (Pushover is first/only)
                pushover_root.setExpanded(not bool(nltha_sets))

                # Only expand first result set, rest collapsed
                for idx, result_set in enumerate(pushover_sets):
                    is_first = (idx == 0)
                    # Get the child count before adding to track which item we're adding
                    child_count_before = pushover_root.childCount()
                    pushover_builders.add_pushover_result_set(self, pushover_root, result_set, expand_first_path=is_first)
                    # Explicitly collapse non-first result sets
                    if not is_first:
                        result_set_item = pushover_root.child(child_count_before)
                        if result_set_item:
                            result_set_item.setExpanded(False)
                            # Also collapse all children of non-first result sets
                            for i in range(result_set_item.childCount()):
                                result_set_item.child(i).setExpanded(False)
            
            # Auto-select first selectable item after tree is populated
            QTimer.singleShot(100, self._auto_select_first_item)

    def _auto_select_first_item(self):
        """Automatically expand to first category and select first selectable item."""
        # Find first selectable leaf item (result_type with direction)
        first_item = self._find_first_selectable_item(self.tree.invisibleRootItem())
        
        if first_item:
            # Expand path to item
            parent = first_item.parent()
            while parent:
                parent.setExpanded(True)
                parent = parent.parent()
            
            # Select and trigger the item
            self.tree.setCurrentItem(first_item)
            self.tree.scrollToItem(first_item)
            self.on_item_clicked(first_item, 0)
    
    def _find_first_selectable_item(self, parent_item: QTreeWidgetItem) -> QTreeWidgetItem:
        """Recursively find first selectable item (result_type with direction or pushover items)."""
        for i in range(parent_item.childCount()):
            item = parent_item.child(i)
            data = item.data(0, Qt.ItemDataRole.UserRole)
            
            if data and isinstance(data, dict):
                item_type = data.get("type")
                # Look for selectable leaf nodes
                if item_type in ("result_type", "pushover_curve", "pushover_global_result", 
                                "pushover_wall_result", "pushover_quad_rotation_result",
                                "pushover_column_result", "pushover_beam_result"):
                    return item
            
            # Recursively search children
            found = self._find_first_selectable_item(item)
            if found:
                return found
        
        return None

    def on_item_clicked(self, item: QTreeWidgetItem, column: int):
        """Handle tree item click - delegates to click_handlers module."""
        click_handlers.on_item_clicked(self, item, column)

    def _on_item_expanded(self, item: QTreeWidgetItem):
        """Handle item expansion - collapse sibling result sets and auto-select first item."""
        data = item.data(0, Qt.ItemDataRole.UserRole)
        if not data or not isinstance(data, dict):
            return

        item_type = data.get("type")

        # Only auto-collapse for result set level items (NLTHA or Pushover)
        if item_type not in ("result_set", "pushover_result_set"):
            return

        parent = item.parent()
        if not parent:
            return

        # Collapse all sibling result sets (same parent)
        for i in range(parent.childCount()):
            sibling = parent.child(i)
            if sibling == item:
                continue

            sibling_data = sibling.data(0, Qt.ItemDataRole.UserRole)
            if sibling_data and isinstance(sibling_data, dict):
                sibling_type = sibling_data.get("type")
                # Collapse other result sets and comparison sets
                if sibling_type in ("result_set", "pushover_result_set", "comparison_set"):
                    sibling.setExpanded(False)

        # Auto-select first selectable item within this result set
        QTimer.singleShot(50, lambda: self._auto_select_first_in_subtree(item))

    def _auto_select_first_in_subtree(self, root_item: QTreeWidgetItem):
        """Find and select the first selectable item within a subtree."""
        first_item = self._find_first_selectable_item(root_item)

        if first_item:
            # Expand path to item
            parent = first_item.parent()
            while parent and parent != root_item:
                parent.setExpanded(True)
                parent = parent.parent()

            # Select and trigger the item
            self.tree.setCurrentItem(first_item)
            self.tree.scrollToItem(first_item)
            self.on_item_clicked(first_item, 0)


class _FadeIndicatorOverlay(QWidget):
    """Overlay widget that shows fade gradients at top/bottom to indicate scrollability."""
    
    def __init__(self, container: QWidget, tree: QTreeWidget):
        super().__init__(container)
        self.tree = tree
        self.container = container
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self._show_top_fade = False
        self._show_bottom_fade = False
        self.hide()  # Hidden by default
        
    def update_indicators(self):
        """Update fade indicators based on scroll position."""
        scrollbar = self.tree.verticalScrollBar()
        if not scrollbar:
            self._show_top_fade = False
            self._show_bottom_fade = False
            self.hide()
            return
            
        value = scrollbar.value()
        minimum = scrollbar.minimum()
        maximum = scrollbar.maximum()
        
        # Show top fade if not at top
        self._show_top_fade = value > minimum
        # Show bottom fade if not at bottom
        self._show_bottom_fade = value < maximum
        
        # Update geometry to match container
        if self.container:
            self.setGeometry(0, 0, self.container.width(), self.container.height())
        
        if self._show_top_fade or self._show_bottom_fade:
            self.show()
            self.update()
        else:
            self.hide()
    
    def paintEvent(self, event):
        """Paint fade gradients at top and/or bottom."""
        if not self._show_top_fade and not self._show_bottom_fade:
            return
            
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        height = self.height()
        fade_height = 16  # Height of fade gradient
        
        # Top fade
        if self._show_top_fade:
            gradient = QLinearGradient(0, 0, 0, fade_height)
            gradient.setColorAt(0, QColor(10, 12, 16, 200))  # Background color with opacity
            gradient.setColorAt(1, QColor(10, 12, 16, 0))
            painter.fillRect(0, 0, self.width(), fade_height, gradient)
        
        # Bottom fade
        if self._show_bottom_fade:
            gradient = QLinearGradient(0, height - fade_height, 0, height)
            gradient.setColorAt(0, QColor(10, 12, 16, 0))
            gradient.setColorAt(1, QColor(10, 12, 16, 200))  # Background color with opacity
            painter.fillRect(0, height - fade_height, self.width(), fade_height, gradient)
