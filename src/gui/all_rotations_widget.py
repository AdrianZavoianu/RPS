"""All Rotations widget - scatter plot and histogram showing distribution of quad rotations across all elements."""

import logging

import numpy as np
import pandas as pd
import pyqtgraph as pg
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import (
    QCheckBox,
    QHBoxLayout,
    QVBoxLayout,
    QWidget,
    QTabWidget,
)

from gui.design_tokens import PALETTE

logger = logging.getLogger(__name__)


class AllRotationsWidget(QWidget):
    """Widget for displaying all quad rotations as scatter plot and histogram (Max and Min combined)."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._crosshair_enabled = False  # starts off; checkbox controls this
        self._x_label = "Quad Rotation (%)"
        self.setup_ui()
        self.current_data_max = None
        self.current_data_min = None
        self._show_averages = True

    def setup_ui(self):
        """Setup the UI with tabs for scatter plot and histogram."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        # ── Toolbar row (checkbox lives here) ─────────────────────────
        toolbar = QHBoxLayout()
        toolbar.setContentsMargins(4, 2, 4, 0)
        toolbar.addStretch()

        self._crosshair_cb = QCheckBox("Crosshair")
        self._crosshair_cb.setChecked(False)
        self._crosshair_cb.setToolTip(
            "Show a vertical crosshair with the exact rotation value when hovering over the scatter plot"
        )
        self._crosshair_cb.setStyleSheet(
            """
            QCheckBox {
                color: #94a3b8;
                font-size: 11px;
                spacing: 5px;
            }
            QCheckBox::indicator {
                width: 13px; height: 13px;
                border: 1px solid #475569;
                border-radius: 3px;
                background: #1e293b;
            }
            QCheckBox::indicator:checked {
                background: #06b6d4;
                border-color: #06b6d4;
            }
        """
        )
        self._crosshair_cb.toggled.connect(self._on_crosshair_toggled)
        toolbar.addWidget(self._crosshair_cb)
        layout.addLayout(toolbar)

        # ── Tab widget ────────────────────────────────────────────────
        from gui.design_tokens import FormStyles

        self.tabs = QTabWidget()
        self.tabs.setStyleSheet(FormStyles.tab_widget_minimal())

        # Create scatter plot widget using factory
        from gui.components.plot_factory import create_plot_widget

        self.plot_widget = create_plot_widget(show_border=False, grid_alpha=0.35)
        self.plot_widget.getAxis("bottom").enableAutoSIPrefix(False)

        # ── Crosshair: cyan vertical line with built-in bottom label ──
        _CYAN = "#06b6d4"
        self._vline = pg.InfiniteLine(
            angle=90,
            movable=False,
            pen=pg.mkPen(QColor(_CYAN), width=1, style=Qt.PenStyle.DashLine),
            label="{value:.4f}",
            labelOpts={
                "position": 0.04,  # 0 = bottom of line, 1 = top
                "color": QColor(_CYAN),
                "fill": pg.mkBrush(QColor(15, 23, 42, 200)),  # dark semi-transparent bg
                "movable": False,
            },
        )
        self._vline.setVisible(False)

        self.plot_widget.addItem(self._vline, ignoreBounds=True)

        # Rate-limited mouse-move signal (~60 fps)
        self._mouse_proxy = pg.SignalProxy(
            self.plot_widget.scene().sigMouseMoved,
            rateLimit=60,
            slot=self._on_mouse_moved,
        )
        vb = self.plot_widget.getViewBox()
        vb.hoverEvent = self._on_vb_hover

        # Create histogram widget using factory
        self.histogram_widget = create_plot_widget(
            plot_type="histogram", show_border=False, grid_alpha=0.35
        )
        self.histogram_widget.getAxis("bottom").enableAutoSIPrefix(False)

        # Add tabs
        self.tabs.addTab(self.plot_widget, "Scatter")
        self.tabs.addTab(self.histogram_widget, "Histogram")

        layout.addWidget(self.tabs)

    # ------------------------------------------------------------------
    # Crosshair helpers
    # ------------------------------------------------------------------

    def _on_crosshair_toggled(self, checked: bool):
        """Enable or disable the hover crosshair."""
        self._crosshair_enabled = checked
        if not checked:
            self._vline.setVisible(False)

    def _on_mouse_moved(self, evt):
        """Update the vertical crosshair line on mouse move (only when enabled)."""
        if not self._crosshair_enabled:
            return
        pos = evt[0]  # SignalProxy wraps events in a tuple
        vb = self.plot_widget.getViewBox()
        if not self.plot_widget.sceneBoundingRect().contains(pos):
            self._vline.setVisible(False)
            return

        mouse_point = vb.mapSceneToView(pos)
        self._vline.setPos(mouse_point.x())
        self._vline.setVisible(True)

    def _on_vb_hover(self, ev):
        """Hide crosshair when mouse leaves the ViewBox."""
        if ev.isExit():
            self._vline.setVisible(False)

    def set_x_label(self, label: str):
        """Update the X-axis label for both plots.

        Args:
            label: New X-axis label text
        """
        self._x_label = label
        self.plot_widget.setLabel("bottom", label)
        self.histogram_widget.setLabel("bottom", label)
        self._set_crosshair_label_unit(label)

    def _set_crosshair_label_unit(self, label: str):
        """Keep the hover label unit aligned with the current x-axis label."""
        unit = ""
        if "(" in label and ")" in label:
            unit = label.rsplit("(", 1)[1].split(")", 1)[0].strip()
        elif "[" in label and "]" in label:
            unit = label.rsplit("[", 1)[1].split("]", 1)[0].strip()

        label_format = "{value:.4f}" + (f" {unit}" if unit else "")
        line_label = getattr(self._vline, "label", None)
        if line_label is None:
            return
        if hasattr(line_label, "setFormat"):
            line_label.setFormat(label_format)
        else:
            line_label.format = label_format

    def load_dataset(self, df_max: pd.DataFrame, df_min: pd.DataFrame, show_averages: bool = True):
        """Load and display all rotation data points (both Max and Min).

        Args:
            df_max: DataFrame with Max rotation data (Element, Story, LoadCase, Rotation, StoryOrder, StoryIndex)
            df_min: DataFrame with Min rotation data (Element, Story, LoadCase, Rotation, StoryOrder, StoryIndex)
            show_averages: Whether to plot per-element average markers.
        """
        if (df_max is None or df_max.empty) and (df_min is None or df_min.empty):
            self.clear_data()
            return

        self.current_data_max = df_max
        self.current_data_min = df_min
        self._show_averages = show_averages

        # Update scatter plot
        self._plot_combined_scatter(df_max, df_min)

        # Update histogram
        self._plot_histogram(df_max, df_min)

    def _plot_combined_scatter(self, df_max: pd.DataFrame, df_min: pd.DataFrame):
        """Plot scatter plot with both Max and Min data, story bins, and vertical jitter."""
        self.plot_widget.clear()
        # Re-add persistent crosshair line (clear() removes everything)
        self.plot_widget.addItem(self._vline, ignoreBounds=True)

        # Use whichever dataframe is available to get story info
        df_ref = df_max if df_max is not None and not df_max.empty else df_min
        if df_ref is None or df_ref.empty:
            return

        # Get unique stories in order
        stories_df = df_ref[["Story", "StoryOrder"]].drop_duplicates().sort_values("StoryOrder")
        story_names_excel_order = stories_df["Story"].tolist()

        # REVERSE story order for plotting: bottom floors at bottom (y=0), top floors at top (y=max)
        # Excel typically has top-to-bottom, but we want bottom-to-top for plots
        story_names = list(reversed(story_names_excel_order))
        num_stories = len(story_names)

        # Create story index mapping (0, 1, 2, ... for Y axis)
        # Now 0 = bottom floor, max = top floor
        story_to_index = {name: idx for idx, name in enumerate(story_names)}

        all_x_values = []

        # Define single orange color for all markers
        orange_color = QColor("#f97316")

        # Plot Max data points (small orange circles)
        if df_max is not None and not df_max.empty:
            x_max, y_max, _ = self._prepare_scatter_data(df_max, story_to_index, "Max")
            if x_max:
                scatter_max = pg.ScatterPlotItem(
                    x=x_max,
                    y=y_max,
                    size=4,  # Smaller markers
                    pen=pg.mkPen(None),
                    brush=pg.mkBrush(orange_color),  # All orange
                    symbol="o",
                )
                self.plot_widget.addItem(scatter_max)
                all_x_values.extend(x_max)

        # Plot Min data points (small orange circles)
        if df_min is not None and not df_min.empty:
            x_min, y_min, _ = self._prepare_scatter_data(df_min, story_to_index, "Min")
            if x_min:
                scatter_min = pg.ScatterPlotItem(
                    x=x_min,
                    y=y_min,
                    size=4,  # Smaller markers
                    pen=pg.mkPen(None),
                    brush=pg.mkBrush(orange_color),  # All orange
                    symbol="o",
                )
                self.plot_widget.addItem(scatter_min)
                all_x_values.extend(x_min)

        # --- Average per-hinge markers (blue diamonds) ---
        # Hinge identity: Element + Story (+ Direction if present for column data)
        if self._show_averages:
            avg_x, avg_y = self._compute_hinge_averages(df_max, df_min, story_to_index)
            logger.debug("Hinge averages computed: %d points", len(avg_x))
            if avg_x:
                avg_x_arr = np.array(avg_x, dtype=float)
                avg_y_arr = np.array(avg_y, dtype=float)
                blue_pen = pg.mkPen(QColor("#1e3a8a"), width=1)
                blue_brush = pg.mkBrush(QColor("#2563eb"))
                spots = [
                    {
                        "pos": (float(ax), float(ay)),
                        "size": 11,
                        "symbol": "d",
                        "pen": blue_pen,
                        "brush": blue_brush,
                    }
                    for ax, ay in zip(avg_x_arr, avg_y_arr)
                ]
                scatter_avg = pg.ScatterPlotItem(spots=spots)
                self.plot_widget.addItem(scatter_avg)
                all_x_values.extend(avg_x)

        # Add vertical line at x=0 to show center
        zero_line = pg.InfiniteLine(
            pos=0,
            angle=90,
            pen=pg.mkPen(PALETTE["accent_primary"], width=1, style=Qt.PenStyle.DashLine),
        )
        self.plot_widget.addItem(zero_line)

        # Configure Y-axis with story labels
        y_axis = self.plot_widget.getAxis("left")
        y_ticks = [(idx, name) for idx, name in enumerate(story_names)]
        y_axis.setTicks([y_ticks])

        # Set Y-axis range with padding
        self.plot_widget.setYRange(-0.5, num_stories - 0.5, padding=0)

        # Set X-axis label
        self.plot_widget.setLabel("bottom", self._x_label)
        self.plot_widget.setLabel("left", "Story")

        # Set X-axis range centered at 0 for symmetry
        if all_x_values:
            min_x = min(all_x_values)
            max_x = max(all_x_values)

            # Find the maximum absolute value to create symmetric range
            max_abs = max(abs(min_x), abs(max_x))

            # Add 10% padding
            padding_x = max_abs * 0.1

            # Set symmetric range around 0
            self.plot_widget.setXRange(-(max_abs + padding_x), max_abs + padding_x, padding=0)

    def _compute_hinge_averages(
        self,
        df_max: pd.DataFrame,
        df_min: pd.DataFrame,
        story_to_index: dict,
    ):
        """Compute mean rotation per individual hinge across all ground motions.

        A hinge is identified by (Element, Story) — or (Element, Story, Direction)
        when the Direction column is present (column rotation data).  The mean
        is computed separately for Max and Min envelopes so that Max averages
        plot on the positive side and Min averages on the negative side.

        Returns:
            Tuple of (x_values, y_values) for the blue average markers.
        """
        avg_x: list = []
        avg_y: list = []

        # Determine groupby keys — include Direction when present
        def _group_keys(df: pd.DataFrame) -> list:
            keys = ["Element", "Story"]
            if "Direction" in df.columns:
                keys.append("Direction")
            return keys

        for df in (df_max, df_min):
            if df is None or df.empty:
                continue

            group_keys = _group_keys(df)
            grouped = df.groupby(group_keys)["Rotation"].mean()

            for key_vals, mean_rot in grouped.items():
                # key_vals is a scalar when one group key, tuple otherwise
                if isinstance(key_vals, tuple):
                    story_name = key_vals[1]  # index 1 is always Story
                else:
                    story_name = key_vals  # shouldn't happen given 2+ keys, but safe

                if story_name not in story_to_index:
                    continue

                avg_x.append(mean_rot)
                avg_y.append(float(story_to_index[story_name]))

        return avg_x, avg_y

    def _prepare_scatter_data(self, df: pd.DataFrame, story_to_index: dict, label: str):
        """Prepare scatter data with jitter for a dataset.

        Returns:
            Tuple of (x_values, y_values, colors)
        """
        x_values = []
        y_values = []
        colors = []

        # Get unique stories in the dataframe
        story_names = df["Story"].unique()

        # Use consistent random seed for reproducible jitter
        np.random.seed(42 if label == "Max" else 43)

        for story_name in story_names:
            if story_name not in story_to_index:
                continue

            story_data = df[df["Story"] == story_name]
            story_idx = story_to_index[story_name]

            # Get rotation values for this story
            rotations = story_data["Rotation"].values

            # Apply vertical jitter within ±0.3 of story index
            jitter_range = 0.3
            jitter = np.random.uniform(-jitter_range, jitter_range, len(rotations))
            jittered_y = story_idx + jitter

            x_values.extend(rotations)
            y_values.extend(jittered_y)

            # Color by rotation magnitude
            for rot in rotations:
                colors.append(self._get_rotation_color(rot, label))

        return x_values, y_values, colors

    def _get_rotation_color(self, rotation: float, label: str) -> QColor:
        """Get color based on rotation magnitude and Max/Min type.

        Args:
            rotation: Rotation value in percentage
            label: "Max" or "Min"
        """
        # Normalize rotation to 0-1 range (assuming typical range 0-2%)
        norm_value = min(abs(rotation) / 2.0, 1.0)

        if label == "Max":
            # Max: Blue (#3b82f6) to Orange (#f97316) to Red (#ef4444)
            if norm_value < 0.5:
                # Blue to orange
                t = norm_value * 2
                r = int(59 + (249 - 59) * t)
                g = int(130 + (115 - 130) * t)
                b = int(246 + (22 - 246) * t)
            else:
                # Orange to red
                t = (norm_value - 0.5) * 2
                r = int(249 + (239 - 249) * t)
                g = int(115 + (68 - 115) * t)
                b = int(22 + (68 - 22) * t)
        else:
            # Min: Orange (#f97316) to Red (#ef4444)
            r = int(249 + (239 - 249) * norm_value)
            g = int(115 + (68 - 115) * norm_value)
            b = int(22 + (68 - 22) * norm_value)

        return QColor(r, g, b, 180)  # 70% opacity

    def _plot_histogram(self, df_max: pd.DataFrame, df_min: pd.DataFrame):
        """Plot histogram of all rotation values.

        Args:
            df_max: DataFrame with Max rotation data
            df_min: DataFrame with Min rotation data
        """
        self.histogram_widget.clear()

        # Collect all rotation values
        all_rotations = []
        if df_max is not None and not df_max.empty:
            all_rotations.extend(df_max["Rotation"].values)
        if df_min is not None and not df_min.empty:
            all_rotations.extend(df_min["Rotation"].values)

        if not all_rotations:
            return

        # Calculate histogram with automatic binning
        # Use 50 bins for good resolution
        counts, bin_edges = np.histogram(all_rotations, bins=50)

        # Create bar graph
        bin_width = bin_edges[1] - bin_edges[0]
        x_positions = bin_edges[:-1]  # Use left edge of each bin

        # Create bar chart
        bar_item = pg.BarGraphItem(
            x=x_positions,
            height=counts,
            width=bin_width,
            brush=pg.mkBrush(251, 146, 60, 180),  # Orange with alpha
            pen=pg.mkPen("#fb923c", width=1),
        )
        self.histogram_widget.addItem(bar_item)

        # Add vertical line at x=0 to show center
        zero_line = pg.InfiniteLine(
            pos=0,
            angle=90,
            pen=pg.mkPen(PALETTE["accent_primary"], width=1, style=Qt.PenStyle.DashLine),
        )
        self.histogram_widget.addItem(zero_line)

        # Set axis labels
        self.histogram_widget.setLabel("bottom", self._x_label)
        self.histogram_widget.setLabel("left", "Count")

        # Set Y-axis to start at 0
        max_count = max(counts) if len(counts) > 0 else 1
        self.histogram_widget.setYRange(0, max_count * 1.1, padding=0)

        # Set X-axis range with padding
        min_x = min(all_rotations)
        max_x = max(all_rotations)
        padding_x = (max_x - min_x) * 0.05
        self.histogram_widget.setXRange(min_x - padding_x, max_x + padding_x, padding=0)

    def clear_data(self):
        """Clear all data from plots."""
        self.plot_widget.clear()
        self.histogram_widget.clear()
        # Re-add crosshair line (clear() removes it) and hide until next hover
        self.plot_widget.addItem(self._vline, ignoreBounds=True)
        self._vline.setVisible(False)
        self.current_data_max = None
        self.current_data_min = None
