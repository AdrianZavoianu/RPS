"""Results tree browser - hierarchical navigation for project results.

This is the main browser class that delegates to specialized builder modules
for constructing tree sections.
"""

import logging

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import QTreeWidget, QTreeWidgetItem, QVBoxLayout, QWidget

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

    def setup_ui(self):
        """Setup the browser UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        # Header
        header = create_styled_label("Results Browser", "subheader")
        header.setContentsMargins(12, 8, 12, 8)
        layout.addWidget(header)

        # Tree widget
        self.tree = QTreeWidget()
        self.tree.setHeaderHidden(True)
        self.tree.setIndentation(8)  # Reduced from 16px to 8px for laptop screens
        self.tree.setAnimated(True)
        self.tree.setUniformRowHeights(False)
        self.tree.itemClicked.connect(self.on_item_clicked)

        # Modern minimalist data-vis style (Vercel/Linear inspired)
        self.tree.setStyleSheet("""
            QTreeWidget {
                background-color: transparent;
                border: none;
                outline: none;
                padding: 4px;
                font-size: 14px;
            }
            QTreeWidget::item {
                padding: 7px 10px;
                border-radius: 5px;
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

        layout.addWidget(self.tree)

    def populate_tree(self, result_sets, stories, elements=None, available_result_types=None, comparison_sets=None, pushover_cases=None):
        """Populate tree with project structure.

        Args:
            result_sets: List of ResultSet model instances
            stories: List of Story model instances
            elements: List of Element model instances (optional)
            available_result_types: Dict mapping result_set_id to set of available result types (optional)
            comparison_sets: List of ComparisonSet model instances (optional)
            pushover_cases: Dict mapping result_set_id to list of PushoverCase instances (optional)
        """
        self.tree.clear()
        self.elements = elements or []
        self.available_result_types = available_result_types or {}
        self.comparison_sets = comparison_sets or []
        self.pushover_cases = pushover_cases or {}

        # Project info item
        info_item = QTreeWidgetItem(self.tree)
        info_item.setText(0, f"ⓘ Project Info")
        info_item.setData(0, Qt.ItemDataRole.UserRole, {"type": "info"})
        info_item.setExpanded(False)

        # Add stories count
        stories_info = QTreeWidgetItem(info_item)
        stories_info.setText(0, f"└ {len(stories)} stories")
        stories_info.setFlags(Qt.ItemFlag.NoItemFlags)  # Non-selectable

        # Add result sets count
        sets_info = QTreeWidgetItem(info_item)
        sets_info.setText(0, f"└ {len(result_sets)} result sets")
        sets_info.setFlags(Qt.ItemFlag.NoItemFlags)

        # Results root
        results_root = QTreeWidgetItem(self.tree)
        results_root.setText(0, "▸ Results")
        results_root.setData(0, Qt.ItemDataRole.UserRole, {"type": "root"})
        results_root.setExpanded(True)

        if not result_sets and not self.comparison_sets:
            # Show empty state
            placeholder = QTreeWidgetItem(results_root)
            placeholder.setText(0, "└ No result sets")
            placeholder.setFlags(Qt.ItemFlag.NoItemFlags)
        else:
            # Separate result sets by analysis type
            nltha_sets = [rs for rs in result_sets if getattr(rs, 'analysis_type', 'NLTHA') == 'NLTHA']
            pushover_sets = [rs for rs in result_sets if getattr(rs, 'analysis_type', 'NLTHA') == 'Pushover']

            # NLTHA section (if any NLTHA result sets exist)
            if nltha_sets:
                nltha_root = QTreeWidgetItem(results_root)
                nltha_root.setText(0, "◆ NLTHA")
                nltha_root.setData(0, Qt.ItemDataRole.UserRole, {"type": "analysis_section", "analysis_type": "NLTHA"})
                nltha_root.setExpanded(True)

                for result_set in nltha_sets:
                    nltha_builders.add_result_set(self, nltha_root, result_set)

                # Add comparison sets under NLTHA
                for comparison_set in self.comparison_sets:
                    comparison_builders.add_comparison_set(
                        nltha_root,
                        comparison_set,
                        self.elements,
                    )

            # Pushover section (if any pushover result sets exist)
            if pushover_sets:
                pushover_root = QTreeWidgetItem(results_root)
                pushover_root.setText(0, "◆ Pushover")
                pushover_root.setData(0, Qt.ItemDataRole.UserRole, {"type": "analysis_section", "analysis_type": "Pushover"})
                pushover_root.setExpanded(True)

                # Add each pushover result set
                for result_set in pushover_sets:
                    pushover_builders.add_pushover_result_set(self, pushover_root, result_set)

    def on_item_clicked(self, item: QTreeWidgetItem, column: int):
        """Handle tree item click - delegates to click_handlers module."""
        click_handlers.on_item_clicked(self, item, column)
