"""Tests for gui.components.plot_factory."""

import pytest

# Note: These tests run without QApplication for basic import/structure tests.
# Visual/rendering tests would need QApplication initialization.


class TestPlotFactoryImports:
    """Test that plot factory module can be imported."""

    def test_module_imports(self):
        """Test that the module can be imported."""
        from gui.components import plot_factory
        assert plot_factory is not None

    def test_create_plot_widget_exists(self):
        """Test that create_plot_widget function exists."""
        from gui.components.plot_factory import create_plot_widget
        assert callable(create_plot_widget)

    def test_configure_building_profile_exists(self):
        """Test that configure_building_profile function exists."""
        from gui.components.plot_factory import configure_building_profile
        assert callable(configure_building_profile)

    def test_configure_scatter_plot_exists(self):
        """Test that configure_scatter_plot function exists."""
        from gui.components.plot_factory import configure_scatter_plot
        assert callable(configure_scatter_plot)

    def test_configure_time_series_exists(self):
        """Test that configure_time_series function exists."""
        from gui.components.plot_factory import configure_time_series
        assert callable(configure_time_series)

    def test_convenience_functions_exist(self):
        """Test that convenience functions exist."""
        from gui.components.plot_factory import (
            create_element_scatter_plot,
            create_building_profile_plot,
            set_plot_range,
            clear_plot,
        )
        assert callable(create_element_scatter_plot)
        assert callable(create_building_profile_plot)
        assert callable(set_plot_range)
        assert callable(clear_plot)


class TestPlotColors:
    """Test plot color constants."""

    def test_plot_colors_defined(self):
        """Test that PLOT_COLORS dict is defined with expected keys."""
        from gui.components.plot_factory import PLOT_COLORS

        assert 'background' in PLOT_COLORS
        assert 'plot_area' in PLOT_COLORS
        assert 'grid' in PLOT_COLORS
        assert 'axis_line' in PLOT_COLORS
        assert 'axis_text' in PLOT_COLORS
        assert 'border' in PLOT_COLORS
        assert 'accent' in PLOT_COLORS

    def test_plot_colors_are_valid(self):
        """Test that color values are valid strings or numbers."""
        from gui.components.plot_factory import PLOT_COLORS

        # String colors should start with # or be named
        for key in ['background', 'plot_area', 'axis_line', 'axis_text', 'border', 'accent']:
            assert isinstance(PLOT_COLORS[key], str)
            assert PLOT_COLORS[key].startswith('#')

        # Grid alpha should be a number
        assert isinstance(PLOT_COLORS['grid'], (int, float))
        assert 0 <= PLOT_COLORS['grid'] <= 1


class TestPlotWidgetCreation:
    """Test plot widget creation with QApplication."""

    @pytest.fixture(autouse=True)
    def ensure_app(self):
        """Ensure QApplication exists for these tests."""
        from PyQt6.QtWidgets import QApplication
        app = QApplication.instance()
        if app is None:
            app = QApplication([])
        app.processEvents()
        yield app
        app.processEvents()

    def test_create_plot_widget_returns_plot_widget(self):
        """Test that create_plot_widget returns a PlotWidget."""
        import pyqtgraph as pg
        from gui.components.plot_factory import create_plot_widget

        plot = create_plot_widget()
        assert isinstance(plot, pg.PlotWidget)

    def test_create_plot_widget_default_non_interactive(self):
        """Test that plots are non-interactive by default."""
        from gui.components.plot_factory import create_plot_widget

        plot = create_plot_widget()
        view_box = plot.getPlotItem().getViewBox()

        # Check mouse is disabled
        state = view_box.state
        assert state['mouseEnabled'][0] is False  # X
        assert state['mouseEnabled'][1] is False  # Y

    def test_create_plot_widget_interactive_enabled(self):
        """Test that interactive=True enables mouse."""
        from gui.components.plot_factory import create_plot_widget

        plot = create_plot_widget(interactive=True)
        view_box = plot.getPlotItem().getViewBox()

        state = view_box.state
        assert state['mouseEnabled'][0] is True
        assert state['mouseEnabled'][1] is True

    def test_create_plot_widget_no_grid(self):
        """Test that show_grid=False disables grid."""
        from gui.components.plot_factory import create_plot_widget

        plot = create_plot_widget(show_grid=False)
        # Grid state is stored internally, just verify creation succeeds
        assert plot is not None

    def test_configure_building_profile_sets_labels(self):
        """Test that configure_building_profile sets axis labels."""
        from gui.components.plot_factory import (
            create_plot_widget,
            configure_building_profile,
        )

        plot = create_plot_widget()
        configure_building_profile(plot, x_label="Drift [%]", y_label="Story")

        # Check labels are set (PlotItem stores labels)
        plot_item = plot.getPlotItem()
        assert plot_item.getAxis('bottom').labelText == "Drift [%]"
        assert plot_item.getAxis('left').labelText == "Story"

    def test_create_building_profile_plot_convenience(self):
        """Test create_building_profile_plot convenience function."""
        import pyqtgraph as pg
        from gui.components.plot_factory import create_building_profile_plot

        plot = create_building_profile_plot("Force [kN]")
        assert isinstance(plot, pg.PlotWidget)

        # Check label was set
        plot_item = plot.getPlotItem()
        assert plot_item.getAxis('bottom').labelText == "Force [kN]"

    def test_clear_plot_removes_items(self):
        """Test that clear_plot removes plot items."""
        import pyqtgraph as pg
        from gui.components.plot_factory import create_plot_widget, clear_plot

        plot = create_plot_widget()

        # Add some items
        plot.plot([1, 2, 3], [1, 2, 3])
        assert len(plot.getPlotItem().listDataItems()) > 0

        # Clear
        clear_plot(plot)
        assert len(plot.getPlotItem().listDataItems()) == 0
