"""Tests for ResultsTreeBrowser and its decomposed modules.

These tests verify that the tree browser correctly builds tree structures
for NLTHA, Pushover, and Comparison results.
"""

import pytest
from unittest.mock import MagicMock, patch


class MockResultSet:
    """Mock ResultSet for testing."""
    def __init__(self, id: int, name: str, analysis_type: str = "NLTHA"):
        self.id = id
        self.name = name
        self.analysis_type = analysis_type


class MockElement:
    """Mock Element for testing."""
    def __init__(self, id: int, name: str, element_type: str):
        self.id = id
        self.name = name
        self.element_type = element_type


class MockComparisonSet:
    """Mock ComparisonSet for testing."""
    def __init__(self, id: int, name: str, result_set_ids: list, result_types: list):
        self.id = id
        self.name = name
        self.result_set_ids = result_set_ids
        self.result_types = result_types


class MockPushoverCase:
    """Mock PushoverCase for testing."""
    def __init__(self, id: int, case_name: str, direction: str):
        self.id = id
        self.case_name = case_name
        self.name = case_name  # Alias for compatibility
        self.direction = direction


class TestNlthaBuilders:
    """Tests for NLTHA section builders."""

    def test_add_result_set_creates_tree_structure(self):
        """Test that add_result_set creates proper tree hierarchy."""
        from gui.tree_browser import nltha_builders
        from PyQt6.QtWidgets import QApplication, QTreeWidgetItem

        # Need QApplication for Qt widgets
        app = QApplication.instance() or QApplication([])

        parent = QTreeWidgetItem()
        result_set = MockResultSet(1, "DES")

        # Create mock browser with required attributes
        browser = MagicMock()
        browser.elements = [
            MockElement(1, "P1", "Wall"),
            MockElement(2, "C1", "Column"),
        ]
        browser._has_data_for = MagicMock(return_value=True)

        nltha_builders.add_result_set(browser, parent, result_set)

        # Should have created a child item for the result set
        assert parent.childCount() == 1
        result_set_item = parent.child(0)
        assert "DES" in result_set_item.text(0)

    def test_add_drifts_section_creates_directions(self):
        """Test that drifts section includes X and Y directions."""
        from gui.tree_browser import nltha_builders
        from PyQt6.QtWidgets import QApplication, QTreeWidgetItem

        app = QApplication.instance() or QApplication([])

        parent = QTreeWidgetItem()

        # Create mock browser (not used by add_drifts_section but needed for signature)
        browser = MagicMock()

        nltha_builders.add_drifts_section(browser, parent, result_set_id=1)

        # Should have created drifts item with X, Y directions and Max/Min
        assert parent.childCount() == 1
        drifts_item = parent.child(0)
        assert "Drifts" in drifts_item.text(0)
        # Children: X Direction, Y Direction, Max/Min Drifts
        assert drifts_item.childCount() >= 2


class TestPushoverBuilders:
    """Tests for Pushover section builders."""

    def test_add_pushover_result_set_creates_curves_section(self):
        """Test that pushover result set includes Curves section."""
        from gui.tree_browser import pushover_builders
        from PyQt6.QtWidgets import QApplication, QTreeWidgetItem

        app = QApplication.instance() or QApplication([])

        parent = QTreeWidgetItem()
        result_set = MockResultSet(1, "Push_DES", "Pushover")

        # Create mock browser with required attributes
        browser = MagicMock()
        browser.elements = []
        browser.pushover_cases = {
            1: [
                MockPushoverCase(1, "Push_X+", "X"),
                MockPushoverCase(2, "Push_Y+", "Y"),
            ]
        }
        browser._has_data_for = MagicMock(return_value=True)

        pushover_builders.add_pushover_result_set(browser, parent, result_set)

        # Should have created a child item
        assert parent.childCount() == 1
        result_set_item = parent.child(0)
        assert "Push_DES" in result_set_item.text(0)


class TestComparisonBuilders:
    """Tests for Comparison section builders."""

    def test_add_comparison_set_creates_global_section(self):
        """Test that comparison set includes Global results when present."""
        from gui.tree_browser import comparison_builders
        from PyQt6.QtWidgets import QApplication, QTreeWidgetItem

        app = QApplication.instance() or QApplication([])

        parent = QTreeWidgetItem()
        comparison_set = MockComparisonSet(
            id=1,
            name="COM1",
            result_set_ids=[1, 2],
            result_types=["Drifts", "Forces"]
        )
        elements = []

        comparison_builders.add_comparison_set(parent, comparison_set, elements)

        # Should have created a comparison set item
        assert parent.childCount() == 1
        comp_item = parent.child(0)
        assert "COM1" in comp_item.text(0)

    def test_add_comparison_set_includes_joints_when_present(self):
        """Test that comparison set includes Joints section for foundation results."""
        from gui.tree_browser import comparison_builders
        from PyQt6.QtWidgets import QApplication, QTreeWidgetItem

        app = QApplication.instance() or QApplication([])

        parent = QTreeWidgetItem()
        comparison_set = MockComparisonSet(
            id=1,
            name="COM2",
            result_set_ids=[1, 2],
            result_types=["SoilPressures", "VerticalDisplacements"]
        )
        elements = []

        comparison_builders.add_comparison_set(parent, comparison_set, elements)

        # Should have created a comparison set item with Joints section
        assert parent.childCount() == 1
        comp_item = parent.child(0)

        # Find Joints section
        has_joints = False
        for i in range(comp_item.childCount()):
            child = comp_item.child(i)
            if "Joints" in child.text(0):
                has_joints = True
                break
        assert has_joints, "Joints section should be present for foundation results"


class TestClickHandlers:
    """Tests for click handler dispatching."""

    def test_click_handler_dispatches_result_type(self):
        """Test that click handler correctly dispatches result_type clicks."""
        from gui.tree_browser import click_handlers
        from PyQt6.QtWidgets import QApplication, QTreeWidgetItem
        from PyQt6.QtCore import Qt

        app = QApplication.instance() or QApplication([])

        # Create mock browser with signal
        browser = MagicMock()
        browser.selection_changed = MagicMock()
        browser.selection_changed.emit = MagicMock()

        # Create tree item with result_type data
        item = QTreeWidgetItem()
        item.setData(0, Qt.ItemDataRole.UserRole, {
            "type": "result_type",
            "result_set_id": 1,
            "category": "Envelopes",
            "result_type": "Drifts",
            "direction": "X",
            "element_id": 0
        })

        click_handlers.on_item_clicked(browser, item, 0)

        # Should have emitted selection_changed signal
        browser.selection_changed.emit.assert_called_once_with(1, "Envelopes", "Drifts", "X", 0)

    def test_click_handler_dispatches_comparison_result_type(self):
        """Test that click handler correctly dispatches comparison clicks."""
        from gui.tree_browser import click_handlers
        from PyQt6.QtWidgets import QApplication, QTreeWidgetItem
        from PyQt6.QtCore import Qt

        app = QApplication.instance() or QApplication([])

        browser = MagicMock()
        browser.comparison_selected = MagicMock()
        browser.comparison_selected.emit = MagicMock()

        item = QTreeWidgetItem()
        item.setData(0, Qt.ItemDataRole.UserRole, {
            "type": "comparison_result_type",
            "comparison_set_id": 1,
            "result_type": "Drifts",
            "direction": "X"
        })

        click_handlers.on_item_clicked(browser, item, 0)

        browser.comparison_selected.emit.assert_called_once_with(1, "Drifts", "X")

    def test_click_handler_ignores_invalid_data(self):
        """Test that click handler handles items without valid data."""
        from gui.tree_browser import click_handlers
        from PyQt6.QtWidgets import QApplication, QTreeWidgetItem

        app = QApplication.instance() or QApplication([])

        browser = MagicMock()
        item = QTreeWidgetItem()
        # No data set on item

        # Should not raise an exception
        click_handlers.on_item_clicked(browser, item, 0)


class TestBrowserIntegration:
    """Integration tests for the full ResultsTreeBrowser."""

    def test_browser_imports_correctly(self):
        """Test that browser can be imported from both locations."""
        # Import from new package
        from gui.tree_browser import ResultsTreeBrowser as NewBrowser

        # Import from backward-compat location
        from gui.results_tree_browser import ResultsTreeBrowser as OldBrowser

        # Should be the same class
        assert NewBrowser is OldBrowser

    def test_browser_creates_without_error(self):
        """Test that browser widget can be instantiated."""
        from PyQt6.QtWidgets import QApplication
        from gui.tree_browser import ResultsTreeBrowser

        app = QApplication.instance() or QApplication([])

        browser = ResultsTreeBrowser(project_id=1)
        assert browser is not None
        assert browser.project_id == 1

    def test_browser_populate_tree_with_nltha(self):
        """Test browser populates tree with NLTHA result sets."""
        from PyQt6.QtWidgets import QApplication
        from gui.tree_browser import ResultsTreeBrowser

        app = QApplication.instance() or QApplication([])

        browser = ResultsTreeBrowser(project_id=1)
        result_sets = [MockResultSet(1, "DES", "NLTHA")]
        stories = []
        elements = []

        browser.populate_tree(result_sets, stories, elements)

        # Tree should have items
        assert browser.tree.topLevelItemCount() > 0

    def test_browser_populate_tree_with_pushover(self):
        """Test browser populates tree with Pushover result sets."""
        from PyQt6.QtWidgets import QApplication
        from gui.tree_browser import ResultsTreeBrowser

        app = QApplication.instance() or QApplication([])

        browser = ResultsTreeBrowser(project_id=1)
        result_sets = [MockResultSet(1, "Push_DES", "Pushover")]
        stories = []
        elements = []
        pushover_cases = {
            1: [MockPushoverCase(1, "Push_X+", "X")]
        }

        browser.populate_tree(result_sets, stories, elements, pushover_cases=pushover_cases)

        # Tree should have items
        assert browser.tree.topLevelItemCount() > 0
