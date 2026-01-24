"""Tests for ProjectDetailWindow and its decomposed modules.

These tests verify the project detail window components work correctly
after the decomposition refactoring.
"""

import pytest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch


class TestProjectDetailImports:
    """Tests for import compatibility."""

    def test_imports_from_new_package(self):
        """Test that ProjectDetailWindow can be imported from new package."""
        from gui.project_detail import ProjectDetailWindow
        assert ProjectDetailWindow is not None

    # Backward-compat wrapper tests removed - wrapper files deleted in v2.23


class TestViewLoaders:
    """Tests for view loader functions."""

    def test_view_loaders_module_exists(self):
        """Test that view_loaders module can be imported."""
        from gui.project_detail import view_loaders
        assert view_loaders is not None

    def test_view_loaders_has_load_functions(self):
        """Test that view_loaders has expected load functions."""
        from gui.project_detail import view_loaders

        # Check for key functions
        assert hasattr(view_loaders, 'load_standard_dataset')
        assert hasattr(view_loaders, 'load_element_dataset')
        assert hasattr(view_loaders, 'load_maxmin_dataset')
        assert hasattr(view_loaders, 'load_pushover_curve')
        assert hasattr(view_loaders, 'load_all_rotations')


class TestEventHandlers:
    """Tests for event handler functions."""

    def test_event_handlers_module_exists(self):
        """Test that event_handlers module can be imported."""
        from gui.project_detail import event_handlers
        assert event_handlers is not None

    def test_event_handlers_has_handler_functions(self):
        """Test that event_handlers has expected handler functions."""
        from gui.project_detail import event_handlers

        assert hasattr(event_handlers, 'on_browser_selection_changed')
        assert hasattr(event_handlers, 'on_comparison_selected')
        assert hasattr(event_handlers, 'on_comparison_element_selected')

    def test_on_browser_selection_changed_signature(self):
        """Test that handler function has expected parameters."""
        from gui.project_detail import event_handlers
        import inspect

        sig = inspect.signature(event_handlers.on_browser_selection_changed)
        params = list(sig.parameters.keys())

        # Should have: window, result_set_id, category, result_type, direction, element_id
        assert 'window' in params
        assert 'result_set_id' in params
        assert 'category' in params
        assert 'result_type' in params
        assert 'direction' in params
        assert 'element_id' in params

    def test_event_handler_selection_changed(self):
        """Standard selection triggers dataset load and selection update."""
        from gui.project_detail import event_handlers

        window = SimpleNamespace()
        window.data_service = MagicMock()
        window.data_service.get_result_set_by_id.return_value = SimpleNamespace(analysis_type="NLTHA")
        window._switch_context = MagicMock()
        window.controller = MagicMock()
        window.content_area = MagicMock()
        window.content_area.show_standard = MagicMock()

        with patch("gui.project_detail.view_loaders.load_standard_dataset") as load_standard:
            event_handlers.on_browser_selection_changed(
                window=window,
                result_set_id=1,
                category="Envelopes",
                result_type="Drifts",
                direction="X",
                element_id=0,
            )

            window._switch_context.assert_called_with("NLTHA")
            window.controller.update_selection.assert_called_with(
                result_type="Drifts",
                result_set_id=1,
                direction="X",
                element_id=0,
            )
            load_standard.assert_called_once()

    def test_context_switching(self):
        """Pushover result sets switch the active context."""
        from gui.project_detail import event_handlers

        window = SimpleNamespace()
        window.data_service = MagicMock()
        window.data_service.get_result_set_by_id.return_value = SimpleNamespace(analysis_type="Pushover")
        window._switch_context = MagicMock()
        window.controller = MagicMock()
        window.content_area = MagicMock()
        window.content_area.show_standard = MagicMock()

        with patch("gui.project_detail.view_loaders.load_standard_dataset"):
            event_handlers.on_browser_selection_changed(
                window=window,
                result_set_id=2,
                category="Envelopes",
                result_type="Drifts",
                direction="X",
                element_id=0,
            )

            window._switch_context.assert_called_with("Pushover")


class TestViewLoaderCaching:
    """Tests for controller caching helpers."""

    def test_view_loader_caching(self):
        """Pushover mapping cached per result set."""
        from gui.controllers.project_detail_controller import ProjectDetailController

        cache_repo = MagicMock()
        cache_repo.get_distinct_load_cases.return_value = ["LC1_X", "LC1_Y"]

        controller = ProjectDetailController(project_id=1, cache_repo=cache_repo)
        mapping_first = controller.get_pushover_mapping(10)
        mapping_second = controller.get_pushover_mapping(10)

        assert cache_repo.get_distinct_load_cases.call_count == 1
        assert mapping_first == mapping_second
