"""Animated time series view for building profile visualization.

Displays four plots (Displacements, Drifts, Accelerations, Shears) that animate
through time steps, showing the building response over the duration of the analysis.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

import numpy as np
from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel,
    QPushButton, QSlider, QFrame, QSizePolicy,
)
from PyQt6.QtGui import QColor
import pyqtgraph as pg

from gui.styles import COLORS
from gui.ui_helpers import create_styled_button

logger = logging.getLogger(__name__)


@dataclass
class TimeSeriesPlotData:
    """Data container for a single result type's time series."""

    result_type: str  # 'Drifts', 'Forces', 'Displacements', 'Accelerations'
    direction: str  # 'X' or 'Y'
    stories: List[str]  # Story names in building order (top to bottom)
    time_steps: List[float]  # Time values
    values_matrix: np.ndarray  # Shape: (num_stories, num_time_steps)
    unit: str  # Display unit


class AnimatedBuildingProfilePlot(QWidget):
    """Single animated plot showing building profile at each time step."""

    def __init__(self, title: str, unit: str, parent=None):
        super().__init__(parent)
        self.title = title
        self.unit = unit
        self.data: Optional[TimeSeriesPlotData] = None
        self.current_step = 0

        self._setup_ui()

    def _setup_ui(self):
        """Create the plot widget."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        # Title label
        self.title_label = QLabel(self.title)
        self.title_label.setStyleSheet(f"""
            color: {COLORS['text']};
            font-weight: bold;
            font-size: 13px;
            padding: 4px;
        """)
        self.title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.title_label)

        # Plot widget using factory
        pg.setConfigOptions(antialias=True)
        from gui.components.plot_factory import create_plot_widget
        self.plot_widget = create_plot_widget(grid_alpha=0.3)

        layout.addWidget(self.plot_widget)

        # Current profile line (will be updated during animation)
        self.profile_line = self.plot_widget.plot(
            [], [],
            pen=pg.mkPen(COLORS['accent'], width=3),
            symbol='o',
            symbolSize=6,
            symbolBrush=COLORS['accent'],
        )

        # Envelope lines (max/min over all time)
        self.max_line = self.plot_widget.plot(
            [], [],
            pen=pg.mkPen('#e74c3c', width=1, style=Qt.PenStyle.DashLine),
        )
        self.min_line = self.plot_widget.plot(
            [], [],
            pen=pg.mkPen('#3498db', width=1, style=Qt.PenStyle.DashLine),
        )

    def set_data(self, data: TimeSeriesPlotData):
        """Set the time series data for this plot."""
        self.data = data
        self.current_step = 0

        if data is None or data.values_matrix.size == 0:
            self.clear()
            return

        # Calculate envelope (max/min over all time steps)
        self.max_envelope = np.max(data.values_matrix, axis=1)
        self.min_envelope = np.min(data.values_matrix, axis=1)

        # Set up y-axis (stories) - data comes in ascending order (lowest floor first)
        # so position 0 = bottom = first story in list (lowest floor)
        num_stories = len(data.stories)
        story_positions = list(range(num_stories))

        # Configure y-axis with story labels (position 0 = bottom = lowest floor)
        y_axis = self.plot_widget.getAxis('left')
        ticks = [(i, data.stories[i]) for i in story_positions]
        y_axis.setTicks([ticks])

        # Set x-axis label
        self.plot_widget.setLabel('bottom', self.unit)

        # Calculate x-range from envelope
        x_min = np.min(self.min_envelope)
        x_max = np.max(self.max_envelope)
        x_padding = (x_max - x_min) * 0.1 if x_max != x_min else 1.0
        self.plot_widget.setXRange(x_min - x_padding, x_max + x_padding)
        self.plot_widget.setYRange(-0.5, num_stories - 0.5)

        # Draw envelope lines (data already in correct order)
        self.max_line.setData(self.max_envelope, story_positions)
        self.min_line.setData(self.min_envelope, story_positions)

        # Draw initial profile
        self.update_frame(0)

    def update_frame(self, position: float):
        """Update the plot for a specific time position (supports fractional for interpolation).

        Args:
            position: Float position where integer part is the step index and
                      fractional part is the interpolation factor to the next step.
        """
        if self.data is None:
            return

        num_steps = self.data.values_matrix.shape[1]
        if num_steps == 0:
            return

        # Get integer step and interpolation factor
        step = int(position)
        interp_factor = position - step

        # Clamp to valid range
        if step >= num_steps - 1:
            step = num_steps - 1
            interp_factor = 0.0
        elif step < 0:
            step = 0
            interp_factor = 0.0

        self.current_step = step

        # Get values at current step
        values_current = self.data.values_matrix[:, step]

        # Interpolate with next step if we have a fractional component
        if interp_factor > 0 and step < num_steps - 1:
            values_next = self.data.values_matrix[:, step + 1]
            values = values_current + interp_factor * (values_next - values_current)
        else:
            values = values_current

        story_positions = list(range(len(values)))
        self.profile_line.setData(values, story_positions)

    def clear(self):
        """Clear the plot."""
        self.profile_line.setData([], [])
        self.max_line.setData([], [])
        self.min_line.setData([], [])
        self.data = None


class TimeSeriesAnimatedView(QWidget):
    """Container widget with four animated plots and playback controls."""

    time_changed = pyqtSignal(float)  # Current time value

    # Number of interpolation sub-frames between each data step
    INTERP_FRAMES = 4  # 4 sub-frames means smoother transitions

    def __init__(self, parent=None):
        super().__init__(parent)

        self.time_steps: List[float] = []
        self.current_step = 0  # Integer step for slider
        self._current_position = 0.0  # Float position for interpolation
        self.is_playing = False
        self.playback_speed = 50  # ms per frame

        self._setup_ui()
        self._setup_timer()

    def _setup_ui(self):
        """Create the layout with four plots and controls."""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(8, 8, 8, 8)
        main_layout.setSpacing(8)

        # Header with time indicator only (direction removed)
        header_layout = QHBoxLayout()
        header_layout.addStretch()

        self.time_label = QLabel("Time: 0.00s")
        self.time_label.setStyleSheet(f"""
            color: {COLORS['accent']};
            font-weight: bold;
            font-size: 16px;
        """)
        header_layout.addWidget(self.time_label)
        header_layout.addStretch()
        main_layout.addLayout(header_layout)

        # Four plots in single row (1x4 horizontal layout)
        plot_layout = QHBoxLayout()
        plot_layout.setSpacing(12)

        self.displacement_plot = AnimatedBuildingProfilePlot("Displacements", "mm")
        self.drift_plot = AnimatedBuildingProfilePlot("Drifts", "%")
        self.acceleration_plot = AnimatedBuildingProfilePlot("Accelerations", "g")
        self.force_plot = AnimatedBuildingProfilePlot("Shears", "kN")

        plot_layout.addWidget(self.displacement_plot)
        plot_layout.addWidget(self.drift_plot)
        plot_layout.addWidget(self.acceleration_plot)
        plot_layout.addWidget(self.force_plot)

        main_layout.addLayout(plot_layout, 1)

        # Base story acceleration time series plot (full width)
        self.base_accel_plot = self._create_base_acceleration_plot()
        main_layout.addWidget(self.base_accel_plot)

        # Playback controls
        controls_frame = QFrame()
        controls_frame.setStyleSheet(f"""
            QFrame {{
                background-color: {COLORS['card']};
                border: 1px solid {COLORS['border']};
                border-radius: 4px;
                padding: 8px;
            }}
        """)
        controls_layout = QHBoxLayout(controls_frame)
        controls_layout.setContentsMargins(12, 8, 12, 8)
        controls_layout.setSpacing(12)

        # Play/Pause button
        self.play_btn = create_styled_button("▶ Play", "primary", "sm")
        self.play_btn.setFixedWidth(80)
        self.play_btn.clicked.connect(self._toggle_playback)
        controls_layout.addWidget(self.play_btn)

        # Reset button
        self.reset_btn = create_styled_button("⟲ Reset", "secondary", "sm")
        self.reset_btn.setFixedWidth(80)
        self.reset_btn.clicked.connect(self._reset_playback)
        controls_layout.addWidget(self.reset_btn)

        # Time slider
        self.time_slider = QSlider(Qt.Orientation.Horizontal)
        self.time_slider.setMinimum(0)
        self.time_slider.setMaximum(100)
        self.time_slider.setValue(0)
        self.time_slider.setStyleSheet(f"""
            QSlider::groove:horizontal {{
                background: {COLORS['border']};
                height: 6px;
                border-radius: 3px;
            }}
            QSlider::handle:horizontal {{
                background: {COLORS['accent']};
                width: 16px;
                height: 16px;
                margin: -5px 0;
                border-radius: 8px;
            }}
            QSlider::sub-page:horizontal {{
                background: {COLORS['accent']};
                border-radius: 3px;
            }}
        """)
        self.time_slider.valueChanged.connect(self._on_slider_changed)
        controls_layout.addWidget(self.time_slider, 1)

        # Speed control with prominent buttons
        controls_layout.addSpacing(8)

        # Slower button with clear visual styling
        self.slower_btn = QPushButton("◀◀ Slower")
        self.slower_btn.setFixedWidth(90)
        self.slower_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: #1e3a5f;
                border: 2px solid #3498db;
                border-radius: 4px;
                padding: 6px 10px;
                color: #3498db;
                font-weight: bold;
                font-size: 12px;
            }}
            QPushButton:hover {{
                background-color: #2a4a6f;
                border-color: #5dade2;
                color: #5dade2;
            }}
            QPushButton:pressed {{
                background-color: #163050;
            }}
            QPushButton:disabled {{
                background-color: {COLORS['card']};
                border-color: {COLORS['border']};
                color: {COLORS['text_secondary']};
            }}
        """)
        self.slower_btn.clicked.connect(self._decrease_speed)
        controls_layout.addWidget(self.slower_btn)

        # Speed indicator label
        self.speed_label = QLabel("1.0x")
        self.speed_label.setFixedWidth(50)
        self.speed_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.speed_label.setStyleSheet(f"""
            QLabel {{
                background-color: {COLORS['background']};
                border: 1px solid {COLORS['border']};
                border-radius: 4px;
                padding: 4px 8px;
                color: {COLORS['accent']};
                font-weight: bold;
                font-size: 13px;
            }}
        """)
        controls_layout.addWidget(self.speed_label)

        # Faster button with clear visual styling
        self.faster_btn = QPushButton("Faster ▶▶")
        self.faster_btn.setFixedWidth(90)
        self.faster_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: #1e5f3a;
                border: 2px solid #2ecc71;
                border-radius: 4px;
                padding: 6px 10px;
                color: #2ecc71;
                font-weight: bold;
                font-size: 12px;
            }}
            QPushButton:hover {{
                background-color: #2a6f4a;
                border-color: #58d68d;
                color: #58d68d;
            }}
            QPushButton:pressed {{
                background-color: #165030;
            }}
            QPushButton:disabled {{
                background-color: {COLORS['card']};
                border-color: {COLORS['border']};
                color: {COLORS['text_secondary']};
            }}
        """)
        self.faster_btn.clicked.connect(self._increase_speed)
        controls_layout.addWidget(self.faster_btn)

        # Initialize speed index (middle of the range)
        self._speed_index = 5  # Maps to 1.0x
        self._update_speed_display()

        main_layout.addWidget(controls_frame)

    def _create_base_acceleration_plot(self) -> QWidget:
        """Create the base story acceleration time series plot."""
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)

        # Title
        title = QLabel("Base Story Acceleration")
        title.setStyleSheet(f"""
            color: {COLORS['text']};
            font-weight: bold;
            font-size: 12px;
            padding: 2px;
        """)
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        # Plot widget using factory
        from gui.components.plot_factory import create_plot_widget, configure_time_series
        plot_widget = create_plot_widget(grid_alpha=0.3)
        plot_widget.setFixedHeight(112)  # Reduced height (75% of 150px)
        configure_time_series(plot_widget, x_label='Time [s]', y_label='Accel [g]')

        # Elapsed time shading region (from start to current time)
        self._elapsed_region = pg.LinearRegionItem(
            values=[0, 0],
            orientation='vertical',
            brush=pg.mkBrush(74, 125, 137, 50),  # Accent color with low alpha
            pen=pg.mkPen(None),
            movable=False,
        )
        plot_widget.addItem(self._elapsed_region)

        # Time series line
        self._base_accel_line = plot_widget.plot(
            [], [],
            pen=pg.mkPen(COLORS['accent'], width=1.5),
        )

        # Current time marker (vertical line)
        self._time_marker = pg.InfiniteLine(
            pos=0,
            angle=90,
            pen=pg.mkPen('#e74c3c', width=2),
        )
        plot_widget.addItem(self._time_marker)

        layout.addWidget(plot_widget)

        # Store reference
        self._base_accel_plot_widget = plot_widget
        self._base_accel_time_steps = []
        self._base_accel_values = []
        self._base_accel_start_time = 0

        return container

    def _setup_timer(self):
        """Set up the animation timer."""
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._advance_frame)

    def set_data(
        self,
        direction: str,
        displacements: Optional[TimeSeriesPlotData],
        drifts: Optional[TimeSeriesPlotData],
        accelerations: Optional[TimeSeriesPlotData],
        forces: Optional[TimeSeriesPlotData],
    ):
        """Set data for all four plots.

        Args:
            direction: 'X' or 'Y'
            displacements: Displacement time series data
            drifts: Drift time series data
            accelerations: Acceleration time series data
            forces: Shear force time series data
        """
        # Get time steps from any available data
        for data in [displacements, drifts, accelerations, forces]:
            if data is not None and data.time_steps:
                self.time_steps = data.time_steps
                break

        # Update slider range
        if self.time_steps:
            self.time_slider.setMaximum(len(self.time_steps) - 1)
        else:
            self.time_slider.setMaximum(0)

        # Set data for each plot
        self.displacement_plot.set_data(displacements)
        self.drift_plot.set_data(drifts)
        self.acceleration_plot.set_data(accelerations)
        self.force_plot.set_data(forces)

        # Set data for base story acceleration time series
        # Base story is the first story (index 0) after descending sort
        if accelerations is not None and accelerations.values_matrix.size > 0:
            self._base_accel_time_steps = accelerations.time_steps
            # Get base story (first row, index 0 = lowest floor)
            self._base_accel_values = accelerations.values_matrix[0, :]
            self._base_accel_start_time = min(self._base_accel_time_steps)

            # Plot the full time series
            self._base_accel_line.setData(self._base_accel_time_steps, self._base_accel_values)

            # Set axis ranges
            self._base_accel_plot_widget.setXRange(
                self._base_accel_start_time,
                max(self._base_accel_time_steps)
            )
            y_max = max(abs(np.min(self._base_accel_values)), abs(np.max(self._base_accel_values)))
            self._base_accel_plot_widget.setYRange(-y_max * 1.1, y_max * 1.1)

            # Reset elapsed region
            self._elapsed_region.setRegion([self._base_accel_start_time, self._base_accel_start_time])
        else:
            self._base_accel_time_steps = []
            self._base_accel_values = []
            self._base_accel_start_time = 0
            self._base_accel_line.setData([], [])
            self._elapsed_region.setRegion([0, 0])

        # Reset to start
        self._reset_playback()

    def _toggle_playback(self):
        """Toggle play/pause."""
        if self.is_playing:
            self._pause_playback()
        else:
            self._start_playback()

    def _start_playback(self):
        """Start the animation."""
        if not self.time_steps:
            return

        self.is_playing = True
        self.play_btn.setText("⏸ Pause")
        self.timer.start(self.playback_speed)

    def _pause_playback(self):
        """Pause the animation."""
        self.is_playing = False
        self.play_btn.setText("▶ Play")
        self.timer.stop()

    def _reset_playback(self):
        """Reset to the beginning."""
        self._pause_playback()
        self.current_step = 0
        self._current_position = 0.0
        self.time_slider.setValue(0)
        self._update_frame(0)

    def _advance_frame(self):
        """Advance to the next frame with interpolation."""
        if not self.time_steps:
            return

        num_steps = len(self.time_steps)

        # Advance by a fraction of a step for smooth interpolation
        step_increment = 1.0 / self.INTERP_FRAMES
        self._current_position += step_increment

        # Loop back to start when we reach the end
        if self._current_position >= num_steps:
            self._current_position = 0.0

        # Update slider only when we cross an integer boundary
        new_step = int(self._current_position)
        if new_step != self.current_step:
            self.current_step = new_step
            self.time_slider.blockSignals(True)
            self.time_slider.setValue(self.current_step)
            self.time_slider.blockSignals(False)

        self._update_frame_interpolated(self._current_position)

    def _on_slider_changed(self, value: int):
        """Handle slider position change."""
        self.current_step = value
        self._current_position = float(value)  # Sync position with slider
        self._update_frame(value)

    # Speed levels: 0.25x, 0.5x, 0.75x, 1.0x, 1.25x, 1.5x, 2.0x, 2.5x, 3.0x, 4.0x, 5.0x
    SPEED_LEVELS = [
        (0.25, 200),   # 0.25x - very slow (200ms per frame)
        (0.5, 100),    # 0.5x - slow
        (0.75, 67),    # 0.75x - slightly slow
        (1.0, 50),     # 1.0x - normal (50ms per frame)
        (1.25, 40),    # 1.25x - slightly fast
        (1.5, 33),     # 1.5x - fast
        (2.0, 25),     # 2.0x - faster
        (2.5, 20),     # 2.5x - even faster
        (3.0, 17),     # 3.0x - very fast
        (4.0, 12),     # 4.0x - ultra fast
        (5.0, 10),     # 5.0x - maximum (10ms per frame)
    ]

    def _decrease_speed(self):
        """Decrease playback speed (slower)."""
        if self._speed_index > 0:
            self._speed_index -= 1
            self._apply_speed()

    def _increase_speed(self):
        """Increase playback speed (faster)."""
        if self._speed_index < len(self.SPEED_LEVELS) - 1:
            self._speed_index += 1
            self._apply_speed()

    def _apply_speed(self):
        """Apply the current speed setting."""
        multiplier, interval = self.SPEED_LEVELS[self._speed_index]
        self.playback_speed = interval
        if self.is_playing:
            self.timer.setInterval(self.playback_speed)
        self._update_speed_display()

    def _update_speed_display(self):
        """Update the speed indicator label and button states."""
        multiplier, _ = self.SPEED_LEVELS[self._speed_index]
        self.speed_label.setText(f"{multiplier}x")

        # Update button enabled states
        self.slower_btn.setEnabled(self._speed_index > 0)
        self.faster_btn.setEnabled(self._speed_index < len(self.SPEED_LEVELS) - 1)

    def _update_frame(self, step: int):
        """Update all plots for a specific integer time step."""
        self._update_frame_interpolated(float(step))

    def _update_frame_interpolated(self, position: float):
        """Update all plots for a fractional time position (with interpolation).

        Args:
            position: Float position where integer part is the step index and
                      fractional part is the interpolation factor to the next step.
        """
        if not self.time_steps:
            return

        num_steps = len(self.time_steps)
        step = int(position)
        interp_factor = position - step

        # Clamp to valid range
        if step >= num_steps - 1:
            step = num_steps - 1
            interp_factor = 0.0
        elif step < 0:
            step = 0
            interp_factor = 0.0

        # Interpolate time value for display
        time_val = self.time_steps[step]
        if interp_factor > 0 and step < num_steps - 1:
            time_val += interp_factor * (self.time_steps[step + 1] - self.time_steps[step])

        self.time_label.setText(f"Time: {time_val:.2f}s")
        self.time_changed.emit(time_val)

        # Update time marker on base acceleration plot
        self._time_marker.setValue(time_val)

        # Update elapsed time shading region
        self._elapsed_region.setRegion([self._base_accel_start_time, time_val])

        # Update each plot with fractional position for smooth interpolation
        self.displacement_plot.update_frame(position)
        self.drift_plot.update_frame(position)
        self.acceleration_plot.update_frame(position)
        self.force_plot.update_frame(position)

    def clear(self):
        """Clear all plots."""
        self._pause_playback()
        self.time_steps = []
        self.current_step = 0
        self._current_position = 0.0
        self.time_slider.setValue(0)
        self.time_slider.setMaximum(0)
        self.time_label.setText("Time: 0.00s")

        self.displacement_plot.clear()
        self.drift_plot.clear()
        self.acceleration_plot.clear()
        self.force_plot.clear()

        # Clear base acceleration plot
        self._base_accel_time_steps = []
        self._base_accel_values = []
        self._base_accel_start_time = 0
        self._base_accel_line.setData([], [])
        self._time_marker.setValue(0)
        self._elapsed_region.setRegion([0, 0])
