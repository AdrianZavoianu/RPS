"""Combined Responses Widget - displays side-by-side profiles for Displacements, Drifts, Accelerations, Forces."""

from __future__ import annotations

from types import MethodType

import pandas as pd
import pyqtgraph as pg
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QLabel,
    QVBoxLayout,
    QWidget,
)

from config.visual_config import series_color, ZERO_LINE_COLOR
from gui.components.plot_factory import create_building_profile_plot, set_plot_range
from gui.maxmin_data_processor import MaxMinDataProcessor
from utils.plot_builder import PlotBuilder
from config.result_config import get_config


class CombinedResponsesWidget(QWidget):
    """Widget displaying 4 side-by-side response envelope plots for a selected loadcase."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._data_processor = MaxMinDataProcessor()
        
        self.datasets = {}  # type_name -> MaxMinDataset
        self.story_names = []
        self.load_cases = []
        
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(16)

        # Controls Header
        controls_layout = QHBoxLayout()
        controls_layout.setAlignment(Qt.AlignmentFlag.AlignLeft)
        
        self.loadcase_combo = QComboBox()
        self.loadcase_combo.currentIndexChanged.connect(self._on_combo_changed)
        controls_layout.addWidget(QLabel("Load Case:"))
        controls_layout.addWidget(self.loadcase_combo)
        
        controls_layout.addSpacing(20)
        
        self.envelope_combo = QComboBox()
        self.envelope_combo.addItems(["X Max", "X Min", "Y Max", "Y Min"])
        self.envelope_combo.currentIndexChanged.connect(self._on_combo_changed)
        controls_layout.addWidget(QLabel("Envelope:"))
        controls_layout.addWidget(self.envelope_combo)
        
        layout.addLayout(controls_layout)

        # Plots Layout
        plots_layout = QHBoxLayout()
        plots_layout.setSpacing(10)
        
        # Plot configurations
        self.plot_configs = [
            ("Displacements", "Displacements"),
            ("Drifts", "Drifts"),
            ("Accelerations", "Accelerations"),
            ("Forces", "Story Forces")
        ]
        
        self.plots = {}
        for result_type, title in self.plot_configs:
            plot_widget = create_building_profile_plot(x_label="", y_label="Story" if result_type == "Displacements" else "")
            
            # Hide Y-axis for plots after the first one to save space and keep
            # the columns tight together.
            if result_type != "Displacements":
                left_axis = plot_widget.getAxis('left')
                left_axis.setStyle(showValues=False)
                left_axis.setWidth(0)
                plot_widget.setLabel('left', '')
                
            self.plots[result_type] = plot_widget
            plots_layout.addWidget(plot_widget)

        layout.addLayout(plots_layout)

    def load_datasets(self, datasets: dict[str, 'MaxMinDataset']):
        """Load datasets and initialize the view."""
        self.datasets = datasets
        
        # Extract common information
        if not datasets:
            return
            
        # Build master story list and Y-mapping. MaxMin datasets come in Excel
        # order (roof-first); reverse to ground-first so the building profile
        # matches the orientation of the individual response views.
        self.master_story_labels = []
        source_df = None
        if "Displacements" in datasets:
            source_df = datasets["Displacements"].data
        elif datasets:
            source_df = next(iter(datasets.values())).data

        if source_df is not None:
            self.master_story_labels = self._ground_first_stories(source_df)

        self.story_to_y = {str(name): idx for idx, name in enumerate(self.master_story_labels)}
        
        # Extract load cases from Drifts (or any)
        self.load_cases = []
        if "Drifts" in datasets:
            df = datasets["Drifts"].data
            # Get columns for any direction, just to extract load case names
            max_cols = [col for col in df.columns if "Max_" in col]
            cases = set()
            for col in max_cols:
                # E.g., Max_DES_X
                parts = col.split("_")
                if len(parts) >= 2:
                    cases.add(parts[1])
            self.load_cases = sorted(list(cases))
        
        # Update combo box
        self.loadcase_combo.blockSignals(True)
        self.loadcase_combo.clear()
        self.loadcase_combo.addItem("Average")
        self.loadcase_combo.addItems(self.load_cases)
        self.loadcase_combo.blockSignals(False)
        
        self._update_plots()

    @staticmethod
    def _ground_first_stories(df: pd.DataFrame) -> list:
        """Return story labels ordered ground-first (bottom-to-top).

        MaxMin datasets are stored in Excel order (top story first). The
        individual response views plot bottom-to-top, so we reverse here to
        keep the combined profiles aligned with them.
        """
        stories = df["Story"].tolist() if "Story" in df.columns else []
        stories = [s for s in stories if str(s).lower() != "base"]
        return list(reversed(stories))

    def _on_combo_changed(self):
        self._update_plots()

    def _update_plots(self):
        if not self.datasets:
            return
            
        selected_case = self.loadcase_combo.currentText()
        envelope_selection = self.envelope_combo.currentText()
        direction = envelope_selection.split()[0]  # "X" or "Y"
        bound = envelope_selection.split()[1]      # "Max" or "Min"
        
        for plot_index, (result_type, title) in enumerate(self.plot_configs):
            if result_type not in self.datasets:
                self.plots[result_type].clear()
                continue

            # Give each response type its own (slightly different) color so the
            # four panels are easy to tell apart.
            type_color = series_color(plot_index)

            dataset = self.datasets[result_type]
            df = dataset.data
            # Use the direction-specific config so the horizontal axis label
            # matches the individual response views (e.g. "Drift X [%]",
            # "Story Shear VX (kN)") rather than the base, direction-less label.
            config = get_config(f"{result_type}_{direction}")
            plot_widget = self.plots[result_type]
            plot_widget.clear()
            
            # Add zero line
            plot_widget.addLine(x=0, pen=pg.mkPen(ZERO_LINE_COLOR, width=1, style=Qt.PenStyle.DotLine))
            
            # Determine values to plot
            plot_values = []
            
            # Map Y positions
            row_y_positions = []
            for story in df["Story"]:
                story_str = str(story)
                row_y_positions.append(self.story_to_y.get(story_str, 0))
            
            if selected_case == "Average":
                max_cols, min_cols = self._data_processor.split_direction_columns(df, direction)
                
                if bound == "Max":
                    max_avg = self._data_processor.compute_average_series(df, max_cols)
                    if max_avg is not None:
                        plot_values = max_avg.tolist()
                else:
                    signed_min = self._data_processor.has_signed_min_values(df, min_cols)
                    min_avg = self._data_processor.compute_average_series(df, min_cols, absolute=not signed_min)
                    if min_avg is not None:
                        raw_min = min_avg.tolist()
                        plot_values = raw_min if signed_min else [-val for val in raw_min]

                color = type_color
                width = 3
                style = Qt.PenStyle.SolidLine
            else:
                col = f"{bound}_{selected_case}_{direction}"
                
                if col in df.columns:
                    if bound == "Min":
                        signed_min = self._data_processor.has_signed_min_values(df, [col])
                        if signed_min:
                            plot_values = df[col].values.tolist()
                        else:
                            plot_values = (-df[col]).values.tolist()
                    else:
                        plot_values = df[col].values.tolist()

                color = type_color
                width = 2
                style = Qt.PenStyle.SolidLine

            y_positions = row_y_positions

            all_values = []
                
            # Plot the selected line
            if plot_values and len(plot_values) == len(y_positions):
                plot_widget.plot(
                    plot_values, y_positions,
                    pen=pg.mkPen(color=color, width=width, style=style),
                    antialias=True
                )
                all_values.extend(plot_values)
                
            # Configure axes using PlotBuilder
            builder = PlotBuilder(plot_widget, config)
            builder.setup_axes(self.master_story_labels)
            builder.set_story_range(len(self.master_story_labels), padding=0.5)

            # Keep the "Building Height" left-axis label only on the leftmost
            # plot; setup_axes re-applies it by default, so clear it elsewhere.
            if plot_index == 0:
                plot_widget.setLabel("left", "Building Height")
            else:
                plot_widget.setLabel("left", "")
                plot_widget.getAxis("left").setStyle(showValues=False)
            
            if all_values:
                min_val = min(all_values)
                max_val = max(all_values)
                builder.set_value_range(min_val, max_val, left_padding=0.1, right_padding=0.1)
                builder.set_dynamic_tick_spacing("bottom", min_val, max_val, num_intervals=4)

            # Format the horizontal axis numbers the same way as the individual
            # response views (fixed decimals, no SI "x0.001" scaling for drifts).
            self._configure_bottom_axis(plot_widget, result_type, config)

            # Add custom title above the plot visually
            unit = f" [{config.unit}]" if getattr(config, 'unit', None) else ""
            builder.set_title(f"{title}{unit}")
            plot_widget.getPlotItem().getViewBox().enableAutoRange(enable=False)

    @staticmethod
    def _configure_bottom_axis(plot_widget, result_type: str, config) -> None:
        """Format axis numbers in table units (no PyQtGraph "x0.001" scaling).

        Every response type uses fixed decimals from its config so the values
        read the same way as in the individual response views.
        """
        axis = plot_widget.getAxis("bottom")
        axis.enableAutoSIPrefix(False)
        decimal_places = config.decimal_places

        def fixed_tick_strings(axis_self, values, scale, spacing):
            return [f"{float(value):.{decimal_places}f}" for value in values]

        axis.tickStrings = MethodType(fixed_tick_strings, axis)
