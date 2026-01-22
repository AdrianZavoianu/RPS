"""Results plot widget - PyQtGraph plots with GMP styling."""

from __future__ import annotations

import logging
from typing import Optional

import numpy as np
from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QGridLayout,
    QLabel,
    QFrame,
    QSizePolicy,
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor
import pandas as pd
import pyqtgraph as pg

from utils.plot_builder import PlotBuilder
from processing.result_service import ResultDataset
from config.visual_config import (
    AVERAGE_SERIES_COLOR,
    STORY_PADDING_STANDARD,
    series_color,
)
from gui.components.legend import create_static_legend_item
from gui.settings_manager import settings
from gui.styles import COLORS

logger = logging.getLogger(__name__)


class ResultsPlotWidget(QWidget):
    """Plot widget for visualizing results."""

    SUMMARY_COLUMNS = {"Avg", "Max", "Min"}

    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_dataset: Optional[ResultDataset] = None
        self._plot_legends = {}
        self._plot_items = {}  # Store plot items for highlighting: {load_case: plot_item}
        self._highlighted_case = None  # Track currently highlighted load case
        self._current_selection: set[str] = set()
        self._average_plot_item = None
        self._envelope_fill_item = None  # Store envelope fill for shading
        self._shorthand_mapping: dict = {}  # Full name -> shorthand for legend display
        self.setup_ui()

        # Connect to settings changes
        settings.settings_changed.connect(self._on_settings_changed)

    def setup_ui(self):
        """Setup the plot UI - single plot view (no tabs)."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 8, 0)  # Reduced right margin for spacing at the right of the plot
        layout.setSpacing(0)

        # Configure PyQtGraph to match GMP dark theme
        pg.setConfigOptions(antialias=True)
        pg.setConfigOption('background', '#0a0c10')
        pg.setConfigOption('foreground', '#d1d5db')

        # Single plot container (no tabs)
        self.main_plot = self._create_plot_widget("Building Profile")
        layout.addWidget(self.main_plot)

        # Keep references for backward compatibility with internal methods
        self.envelope_plot = self.main_plot
        self.comparison_plot = self.main_plot
        self.profile_plot = self.main_plot

    def _create_plot_widget(self, title: str) -> QWidget:
        """Create a styled PyQtGraph plot widget with external legend."""
        from gui.components.plot_factory import create_plot_widget

        # Container widget with vertical layout (plot on top, legend below)
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)  # Minimal spacing between plot and legend

        # Create the plot using factory
        plot_widget = create_plot_widget()

        # No title - maximizes plot area
        plot_widget.setTitle(None)

        # Create legend as a separate widget below the plot - minimalistic, no border/fill
        legend_widget = QFrame()
        legend_widget.setStyleSheet("""
            QFrame {
                background-color: transparent;
                border: none;
                border-radius: 0px;
            }
        """)
        legend_widget.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Maximum  # Fit content height, don't expand
        )

        # Use vertical layout for rows, each row uses horizontal layout to distribute items
        # No fixed margins - items will be spaced to fill available width
        legend_layout = QVBoxLayout(legend_widget)
        legend_layout.setContentsMargins(0, 4, 0, 4)  # No left/right margins - items control spacing
        legend_layout.setSpacing(2)  # Minimal vertical space between rows
        legend_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        
        # Store plot widget reference for potential width calculation
        container._plot_widget_ref = plot_widget

        # Add plot and legend to container (vertical stack)
        layout.addWidget(plot_widget, 1)  # Plot stretches
        layout.addWidget(legend_widget, 0)  # Legend below, fixed height

        # Store references
        container._plot_widget = plot_widget
        container._legend_layout = legend_layout  # Now a VBoxLayout
        container._legend_items = []
        container._legend_rows = []  # Store row widgets for horizontal layouts
        container._current_row = None  # Current row widget being populated

        self._plot_legends[container] = legend_layout
        return container

    def _get_plot_from_container(self, container) -> pg.PlotWidget:
        """Extract the PlotWidget from container."""
        return container._plot_widget

    def _add_legend_item(self, container, color: str, label: str, pen_style: Qt.PenStyle = Qt.PenStyle.SolidLine):
        """Add a legend item to the external legend (horizontal rows, items distributed across width)."""
        # For pushover results with shorthand mapping, show "Px1 = Full Name"
        if label in self._shorthand_mapping:
            shorthand = self._shorthand_mapping[label]
            display_label = f"{shorthand} = {label}"
            logger.debug("[OK] Legend matched: '%s' -> '%s'", label, display_label)
        else:
            display_label = label
            if self._shorthand_mapping:
                logger.debug("[!!] Legend not matched: '%s' (mapping has %s entries)", label, len(self._shorthand_mapping))
                if len(self._shorthand_mapping) > 0:
                    logger.debug("Available mapping keys: %s", list(self._shorthand_mapping.keys())[:3])
            else:
                logger.debug("Legend item (no mapping active): '%s'", label)

        # Determine items per row: 2 for mapped labels (longer), 4 for normal labels
        max_cols = 2 if self._shorthand_mapping else 4

        item_widget = create_static_legend_item(color, display_label, pen_style=pen_style)

        # Get or create current row
        if container._current_row is None or len(container._current_row._items) >= max_cols:
            # Create new row with horizontal layout
            row_widget = QWidget()
            row_layout = QHBoxLayout(row_widget)
            # Left margin aligns with plot area (axis width ~45px), right margin (~8px)
            row_layout.setContentsMargins(45, 0, 8, 0)
            row_layout.setSpacing(0)  # Spacing controlled by stretches
            row_widget._items = []  # Track items in this row
            row_widget._layout = row_layout
            row_widget._max_cols = max_cols

            container._legend_layout.addWidget(row_widget)
            container._legend_rows.append(row_widget)
            container._current_row = row_widget

        # Add stretch before item (except first) for even distribution
        if len(container._current_row._items) > 0:
            container._current_row._layout.addStretch(1)

        # Add item to current row
        container._current_row._layout.addWidget(item_widget)
        container._current_row._items.append(item_widget)
        container._legend_items.append(item_widget)

        # If row is full, close row (NO final stretch - last item aligns to right edge)
        if len(container._current_row._items) >= max_cols:
            container._current_row = None

    def _finalize_legend(self, container):
        """Finalize legend - no action needed, items have fixed width."""
        container._current_row = None

    def _on_settings_changed(self, key: str, value):
        """Handle settings changes."""
        if key == "plot_shading_enabled":
            # Re-render the current dataset to apply/remove shading
            if self.current_dataset:
                self.load_dataset(self.current_dataset, self._shorthand_mapping)

    def _add_envelope_fill(self, plot, numeric_df, story_positions, base_index, include_base_anchor):
        """Add a subtle filled area between min and max envelope of all load cases.

        Args:
            plot: The PlotWidget to add the fill to
            numeric_df: DataFrame with numeric values for each load case
            story_positions: List of y-positions for stories
            base_index: Y-position for base anchor (or None)
            include_base_anchor: Whether to include base anchor at 0
        """
        # Calculate min and max at each story level
        min_values = numeric_df.min(axis=1, skipna=True).fillna(0.0).tolist()
        max_values = numeric_df.max(axis=1, skipna=True).fillna(0.0).tolist()
        y_positions = list(story_positions)

        if include_base_anchor:
            min_values = [0.0] + min_values
            max_values = [0.0] + max_values
            y_positions = [base_index] + y_positions

        # Create fill between min and max using FillBetweenItem
        # Convert to numpy arrays for pyqtgraph
        x_min = np.array(min_values)
        x_max = np.array(max_values)
        y = np.array(y_positions)

        # Create curves for min and max envelope
        curve_min = pg.PlotDataItem(x_min, y)
        curve_max = pg.PlotDataItem(x_max, y)

        # Use theme accent color with low opacity for subtle shading
        accent_color = QColor(COLORS['accent'])
        accent_color.setAlphaF(settings.plot_shading_opacity)

        # Create fill between the two curves
        self._envelope_fill_item = pg.FillBetweenItem(
            curve_min, curve_max,
            brush=pg.mkBrush(accent_color)
        )
        plot.addItem(self._envelope_fill_item)

    def load_dataset(self, dataset: ResultDataset, shorthand_mapping: dict = None) -> None:
        """
        Load data and generate plots from a ResultDataset.

        Args:
            dataset: The result dataset to display
            shorthand_mapping: Optional mapping of full names to shorthand for legend display
        """
        self._current_selection.clear()
        self._average_plot_item = None

        # Clear plots FIRST, then set mapping (clear_plots() clears mapping too)
        self.clear_plots()

        # Set dataset and mapping AFTER clearing (clear_plots sets current_dataset to None)
        self.current_dataset = dataset
        self._shorthand_mapping = shorthand_mapping if shorthand_mapping is not None else {}

        logger.debug("Plot received shorthand_mapping: %s, length: %s", shorthand_mapping is not None, len(self._shorthand_mapping))
        if self._shorthand_mapping:
            logger.debug("Sample mapping: %s", list(self._shorthand_mapping.items())[:2])
        else:
            logger.debug("Plot has empty or no mapping")

        df = dataset.data
        if df.empty:
            return

        config = dataset.config

        # Check if this is joint-level data (no Story column)
        has_story_column = 'Story' in df.columns

        if config.plot_mode == "building_profile":
            self._plot_building_profile(dataset)
        elif not has_story_column:
            # Joint-level results (soil pressures, etc.) - no plot, just table
            # Don't generate plots for joint results as they don't have story hierarchy
            pass
        else:
            # For other result types, use building profile view
            self._plot_building_profile(dataset)

    def _data_columns(self, dataset: ResultDataset) -> list[str]:
        """Return columns that represent load cases (exclude Story and summaries)."""
        return list(dataset.load_case_columns)

    def _plot_envelope(self, dataset: ResultDataset):
        """Plot envelope values by story."""
        container = self.envelope_plot
        plot = self._get_plot_from_container(container)
        self._reset_plot(container)

        df = dataset.data
        stories = df['Story'].tolist()
        story_indices = list(range(len(stories)))
        result_type = dataset.meta.result_type or ""

        # Get numeric columns (exclude 'Story' column)
        numeric_cols = self._data_columns(dataset)

        if not numeric_cols:
            return

        # Calculate max value for each story
        max_values = df[numeric_cols].max(axis=1).tolist()

        # Plot as bar chart
        bargraph = pg.BarGraphItem(
            x=story_indices,
            height=max_values,
            width=0.8,
            brush='#4a7d89',
            pen=pg.mkPen('#2c313a', width=1)
        )
        plot.addItem(bargraph)

        # Add to external legend
        self._add_legend_item(container, '#4a7d89', f"Max {result_type}")

        # Configure axes
        axis = plot.getAxis('bottom')
        axis.setTicks([[(i, name) for i, name in enumerate(stories)]])
        plot.setLabel('bottom', 'Story')
        plot.setLabel('left', dataset.config.y_label)

        # No title - maximizes plot area

    def _plot_comparison(self, dataset: ResultDataset):
        """Plot load case comparison."""
        container = self.comparison_plot
        plot = self._get_plot_from_container(container)
        self._reset_plot(container)

        df = dataset.data
        stories = df['Story'].tolist()
        story_indices = list(range(len(stories)))

        # Get numeric columns
        numeric_cols = self._data_columns(dataset)

        if not numeric_cols:
            return

        # Plot up to 10 load cases
        for idx, col in enumerate(numeric_cols[:10]):
            values = df[col].fillna(0).tolist()
            color = series_color(idx)

            plot.plot(
                story_indices,
                values,
                pen=pg.mkPen(color, width=2),
                symbol='o',
                symbolSize=6,
                symbolBrush=color
            )
            self._add_legend_item(container, color, col)

        # Configure axes
        axis = plot.getAxis('bottom')
        axis.setTicks([[(i, name) for i, name in enumerate(stories)]])
        plot.setLabel('bottom', 'Story')
        plot.setLabel('left', dataset.config.y_label)

        # No title - maximizes plot area

    def _plot_profile(self, dataset: ResultDataset):
        """Plot building profile (story height vs max value)."""
        container = self.profile_plot
        plot = self._get_plot_from_container(container)
        self._reset_plot(container)

        df = dataset.data
        stories = df['Story'].tolist()
        story_indices = list(range(len(stories)))

        # Get numeric columns
        numeric_cols = self._data_columns(dataset)

        if not numeric_cols:
            return

        # Calculate max and average for profile
        max_values = df[numeric_cols].max(axis=1).tolist()
        avg_values = df[numeric_cols].mean(axis=1).tolist()

        # Plot as horizontal bars (swap x and y)
        # Max envelope
        plot.plot(
            max_values,
            story_indices,
            pen=pg.mkPen('#e74c3c', width=2),
            symbol='o',
            symbolSize=6,
            symbolBrush='#e74c3c'
        )
        self._add_legend_item(container, '#e74c3c', 'Maximum')

        # Average
        plot.plot(
            avg_values,
            story_indices,
            pen=pg.mkPen('#4a7d89', width=2, style=Qt.PenStyle.DashLine),
            symbol='s',
            symbolSize=5,
            symbolBrush='#4a7d89'
        )
        self._add_legend_item(container, '#4a7d89', 'Avg')

        # Configure axes
        axis = plot.getAxis('left')
        axis.setTicks([[(i, name) for i, name in enumerate(stories)]])
        plot.setLabel('left', 'Story')
        plot.setLabel('bottom', dataset.config.y_label)

        # No title - maximizes plot area

    def _plot_building_profile(self, dataset: ResultDataset):
        """Plot building profile - drift vs height."""
        # Use the envelope plot for the main view
        container = self.envelope_plot
        plot = self._get_plot_from_container(container)
        self._reset_plot(container)

        df = dataset.data
        stories = df['Story'].tolist()

        include_base_anchor = dataset.meta.result_type == "Displacements"
        if include_base_anchor:
            story_labels = ["Base"] + stories
            base_index = 0
            story_positions = [idx + 1 for idx in range(len(stories))]
        else:
            story_labels = stories
            base_index = None
            story_positions = list(range(len(stories)))

        # Get numeric columns (load cases)
        load_case_columns = self._data_columns(dataset)

        if not load_case_columns:
            return

        # Clear plot items dictionary
        self._plot_items.clear()
        self._average_plot_item = None
        self._envelope_fill_item = None

        # Use dataset order for plotting (already aligned bottom-to-top)
        numeric_df = df[load_case_columns].apply(pd.to_numeric, errors='coerce')

        # Check for duplicate column names
        if len(load_case_columns) != len(set(load_case_columns)):
            from collections import Counter
            duplicates = [col for col, count in Counter(load_case_columns).items() if count > 1]
            raise ValueError(f"Duplicate column names found: {duplicates}. This usually means the cache needs to be rebuilt. Please re-import the result set.")

        # Add envelope fill FIRST (so it's behind the lines) if shading is enabled
        if settings.plot_shading_enabled and len(load_case_columns) > 1:
            self._add_envelope_fill(plot, numeric_df, story_positions, base_index, include_base_anchor)

        # Plot each load case as a line
        # When shading is enabled, make lines thinner and more transparent
        shading_active = settings.plot_shading_enabled and len(load_case_columns) > 1
        line_width = 1 if shading_active else 2
        line_alpha = 0.4 if shading_active else 1.0

        for idx, load_case in enumerate(load_case_columns):
            numeric_values = numeric_df[load_case].fillna(0.0).tolist()
            y_positions = list(story_positions)
            if include_base_anchor:
                numeric_values = [0.0] + numeric_values
                y_positions = [base_index] + y_positions

            color = series_color(idx)

            # Apply alpha if shading is active
            if shading_active:
                qcolor = QColor(color)
                qcolor.setAlphaF(line_alpha)
                pen_color = qcolor
            else:
                pen_color = color

            # Plot horizontal (drift on x-axis, story on y-axis)
            plot_item = plot.plot(
                numeric_values,
                y_positions,
                pen=pg.mkPen(pen_color, width=line_width)
            )
            # Store the plot item for later highlighting (store original color for hover/selection)
            self._plot_items[load_case] = {'item': plot_item, 'color': color, 'width': line_width}

            self._add_legend_item(container, color, load_case)

        # Calculate and plot average line (bold, dashed)
        # Skip for pushover results (indicated by empty summary_columns)
        show_average = len(load_case_columns) > 1 and len(dataset.summary_columns) > 0
        if show_average:
            avg_series = numeric_df.mean(axis=1, skipna=True).fillna(0.0)
            avg_values = avg_series.tolist()
            y_positions = list(story_positions)
            if include_base_anchor:
                avg_values = [0.0] + avg_values
                y_positions = [base_index] + y_positions

            # Plot average with bold, dashed line in bright orange
            self._average_plot_item = plot.plot(
                avg_values,
                y_positions,
                pen=pg.mkPen(AVERAGE_SERIES_COLOR, width=5, style=Qt.PenStyle.DashLine)
            )
            self._add_legend_item(container, AVERAGE_SERIES_COLOR, 'Avg', pen_style=Qt.PenStyle.DashLine)

        # Use PlotBuilder for common configuration
        builder = PlotBuilder(plot, dataset.config)

        # Configure axes with story labels
        builder.setup_axes(story_labels)

        # Set y-axis range with tight padding
        builder.set_story_range(len(story_labels), padding=STORY_PADDING_STANDARD)

        # Calculate x-axis range from all values
        all_values = [
            float(value)
            for value in numeric_df.to_numpy().flatten()
            if not pd.isna(value)
        ]
        if include_base_anchor:
            all_values.append(0.0)

        # Filter out zeros and set range with small padding
        all_values = [v for v in all_values if abs(v) > 0.0]
        if all_values:
            min_val = min(all_values)
            max_val = max(all_values)
            if include_base_anchor:
                min_val = min(min_val, 0.0)
                max_val = max(max_val, 0.0)
            # Small padding (3% on left, 5% on right for legend/label space)
            builder.set_value_range(min_val, max_val, left_padding=0.03, right_padding=0.05)

            # Set dynamic tick spacing (6 intervals based on data range)
            builder.set_dynamic_tick_spacing('bottom', min_val, max_val, num_intervals=6)

        # Enable grid with increased visibility
        plot.showGrid(x=True, y=True, alpha=0.5)

        # Finalize legend (add stretch to incomplete last row)
        self._finalize_legend(container)

    def highlight_load_cases(self, selected_cases: list):
        """Highlight multiple selected load cases, dim others, always show average at full opacity."""
        # Store current selection for hover state restoration
        self._current_selection = set(selected_cases) if selected_cases else set()

        if not selected_cases:
            # No selection - restore all to full opacity
            for case_name, case_data in self._plot_items.items():
                item = case_data['item']
                color = case_data['color']
                width = case_data['width']
                item.setPen(pg.mkPen(color, width=width))
        else:
            # Highlight selected cases, dim others
            selected_set = set(selected_cases)

            for case_name, case_data in self._plot_items.items():
                item = case_data['item']
                color = case_data['color']
                width = case_data['width']

                if case_name in selected_set:
                    # Selected case - full opacity, slightly thicker
                    item.setPen(pg.mkPen(color, width=width + 1))
                else:
                    # Non-selected case - reduce opacity significantly
                    from PyQt6.QtGui import QColor
                    qcolor = QColor(color)
                    qcolor.setAlpha(40)  # Much lower opacity (0-255 scale, 40 is ~15%)
                    item.setPen(pg.mkPen(qcolor, width=width))

        # Always keep average line at full opacity and bold
        if hasattr(self, '_average_plot_item') and self._average_plot_item:
            self._average_plot_item.setPen(
                pg.mkPen(AVERAGE_SERIES_COLOR, width=5, style=Qt.PenStyle.DashLine)
            )

    def hover_load_case(self, load_case: str):
        """Temporarily highlight a load case on hover (increase thickness and dim others subtly)."""
        if load_case not in self._plot_items:
            return

        from PyQt6.QtGui import QColor

        # Get current selection state
        current_selection = getattr(self, '_current_selection', set())

        for case_name, case_data in self._plot_items.items():
            item = case_data['item']
            color = case_data['color']
            width = case_data['width']

            if case_name == load_case:
                # Hovered case - make it prominent with thicker line
                item.setPen(pg.mkPen(color, width=width + 2))
            elif case_name in current_selection:
                # Selected but not hovered - keep visible with slight dim
                qcolor = QColor(color)
                qcolor.setAlpha(180)  # Still quite visible (~70%)
                item.setPen(pg.mkPen(qcolor, width=width + 1))
            else:
                # Not selected and not hovered - moderate opacity reduction
                qcolor = QColor(color)
                qcolor.setAlpha(100)  # Medium opacity (~39%)
                item.setPen(pg.mkPen(qcolor, width=width))

        # Keep average at full opacity
        if hasattr(self, '_average_plot_item') and self._average_plot_item:
            self._average_plot_item.setPen(
                pg.mkPen(AVERAGE_SERIES_COLOR, width=5, style=Qt.PenStyle.DashLine)
            )

    def clear_hover(self):
        """Clear hover effect and restore to selected state."""
        # Restore to the current selection state
        if hasattr(self, '_current_selection'):
            self.highlight_load_cases(list(self._current_selection))
        else:
            self.highlight_load_cases([])

    def clear_plots(self):
        """Clear all plots."""
        self._reset_plot(self.envelope_plot)
        self._reset_plot(self.comparison_plot)
        self._reset_plot(self.profile_plot)
        self._plot_items.clear()
        self._highlighted_case = None
        self._average_plot_item = None
        self._envelope_fill_item = None
        self.current_dataset = None
        self._shorthand_mapping.clear()

    def _reset_plot(self, container):
        """Clear plot curves and legend entries."""
        plot = self._get_plot_from_container(container)
        plot.clear()

        # Clear external legend rows
        for row_widget in container._legend_rows:
            container._legend_layout.removeWidget(row_widget)
            row_widget.deleteLater()
        container._legend_rows.clear()
        container._legend_items.clear()
        container._current_row = None
