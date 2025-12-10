"""Pushover curve view - displays displacement vs base shear curves."""

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QSplitter, QTableWidget, QTableWidgetItem, QHeaderView, QFrame
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont
import pyqtgraph as pg


class PushoverCurveView(QWidget):
    """Widget to display pushover curve data (displacement vs base shear)."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._initial_sizes_set = False
        self.setup_ui()

    def setup_ui(self):
        """Setup the view layout with horizontal splitter."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Horizontal splitter (table left, plot right)
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setChildrenCollapsible(False)
        splitter.setHandleWidth(8)
        splitter.setStyleSheet(
            """
            QSplitter {
                padding: 0px;
                margin: 0px;
            }
            QSplitter::handle {
                background-color: transparent;
                margin: 0px 4px;
            }
            """
        )

        # ============ TABLE WIDGET ============
        # Container with no border - can stretch
        from PyQt6.QtWidgets import QSizePolicy
        self.table_container = QWidget()
        self.table_container.setStyleSheet("QWidget { background-color: #0a0c10; border: none; }")  # Match background, no border
        container_layout = QVBoxLayout(self.table_container)
        container_layout.setContentsMargins(0, 0, 0, 0)
        container_layout.setSpacing(0)

        self.table = QTableWidget()
        # Remove native frame; rely only on explicit borders
        self.table.setFrameStyle(QFrame.Shape.NoFrame)
        self.table.setLineWidth(0)
        self.table.setMidLineWidth(0)
        self.table.setShowGrid(True)
        self.table.setColumnCount(3)
        self.table.setHorizontalHeaderLabels(["Step", "Base Shear (kN)", "Displacement (mm)"])
        self.table.setAlternatingRowColors(False)
        self.table.verticalHeader().setVisible(False)

        # DON'T let table expand vertically
        self.table.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)

        # Enable scrollbars when needed
        self.table.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.table.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)

        # Match NLTHA table styling exactly
        table_font = QFont("Inter", 10)
        self.table.setFont(table_font)
        self.table.horizontalHeader().setFont(table_font)

        self.table.setStyleSheet("""
            QTableWidget {
                background-color: #0a0c10;
                border: none;
                outline: none;
                gridline-color: #1e2329;
                color: #d1d5db;
            }
            QTableWidget::item {
                padding: 1px 2px;
                border: none;
            }
            QTableWidget QTableCornerButton::section {
                border: none;
                background-color: #161b22;
            }
            QHeaderView {
                background-color: #161b22;
            }
            QHeaderView::section {
                background-color: #161b22;
                color: #4a7d89;
                padding: 4px 4px;
                border: none;
                border-right: 1px solid #1e2329;
                border-bottom: 1px solid #1e2329;
                font-weight: 600;
                text-align: center;
            }
            QHeaderView::section:last {
                border-right: none;
            }
        """)

        # Fixed column widths - wider to fit header text
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.Fixed)
        header.setStretchLastSection(False)
        header.setDefaultAlignment(Qt.AlignmentFlag.AlignCenter)

        # Set individual column widths
        header.resizeSection(0, 50)   # Step column - narrow
        header.resizeSection(1, 120)  # Base Shear (kN) - wider to fit header
        header.resizeSection(2, 140)  # Displacement (mm) - wider to fit header

        # Lock width to content to avoid extra bordered area
        total_width = header.sectionSize(0) + header.sectionSize(1) + header.sectionSize(2) + 2
        self.table.setMinimumWidth(total_width)
        self.table.setMaximumWidth(total_width)
        self.table.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)

        self.table.setWordWrap(False)

        # Add table to container - stretch=0 means don't expand
        container_layout.addWidget(self.table, stretch=0, alignment=Qt.AlignmentFlag.AlignTop)

        # ============ PLOT WIDGET ============
        # Configure PyQtGraph globally
        pg.setConfigOptions(antialias=True)
        pg.setConfigOption('background', '#0a0c10')
        pg.setConfigOption('foreground', '#d1d5db')

        self.plot_widget = pg.PlotWidget()
        self.plot_widget.setBackground('#0a0c10')

        # Set plot area background to slightly lighter shade
        view_box = self.plot_widget.getPlotItem().getViewBox()
        view_box.setBackgroundColor('#0f1419')

        # Add border to plot area
        view_box.setBorder(pg.mkPen('#2c313a', width=1))

        # Set axis labels
        self.plot_widget.setLabel('left', 'Base Shear', units='kN',
                                  color='#d1d5db', **{'font-size': '12pt'})
        self.plot_widget.setLabel('bottom', 'Displacement', units='mm',
                                  color='#d1d5db', **{'font-size': '12pt'})

        # Grid with proper visibility
        self.plot_widget.showGrid(x=True, y=True, alpha=0.5)

        # Style the axes
        self.plot_widget.getAxis('left').setPen(pg.mkPen('#2c313a', width=1))
        self.plot_widget.getAxis('bottom').setPen(pg.mkPen('#2c313a', width=1))
        self.plot_widget.getAxis('left').setTextPen('#d1d5db')
        self.plot_widget.getAxis('bottom').setTextPen('#d1d5db')

        # Disable auto-SI prefix scaling
        self.plot_widget.getAxis('left').enableAutoSIPrefix(False)
        self.plot_widget.getAxis('bottom').enableAutoSIPrefix(False)

        # Disable menu and mouse interactions
        self.plot_widget.setMenuEnabled(False)
        view_box.setMouseEnabled(x=False, y=False)

        # Set padding for plot - minimal like NLTHA
        view_box.setDefaultPadding(0.0)

        # No title
        self.plot_widget.setTitle(None)

        # Add widgets to splitter
        splitter.addWidget(self.table_container)
        splitter.addWidget(self.plot_widget)

        # Table: content width, stretch factor 1
        # Plot: remaining space, stretch factor 2
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 2)

        layout.addWidget(splitter)
        self._splitter = splitter

    def showEvent(self, event):
        """Set splitter proportions after widget is shown."""
        super().showEvent(event)
        if not self._initial_sizes_set:
            QTimer.singleShot(0, self._apply_splitter_proportions)
            self._initial_sizes_set = True

    def _apply_splitter_proportions(self):
        """Let table take minimum width needed, give remaining space to plot."""
        pass

    def display_curve(self, case_name: str, step_numbers: list, displacements: list, base_shears: list):
        """
        Display pushover curve data.

        Args:
            case_name: Name of the pushover case
            step_numbers: List of step numbers
            displacements: List of displacement values (mm)
            base_shears: List of base shear values (kN)
        """
        # Show table container for single curve view
        self.table_container.show()

        # Clear previous data
        self.table.setRowCount(0)
        self.plot_widget.clear()

        # Ensure table header is visible
        self.table.horizontalHeader().setVisible(True)
        self.table.show()

        if not step_numbers:
            return

        # Populate table (columns: Step, Base Shear, Displacement)
        self.table.setRowCount(len(step_numbers))
        for i in range(len(step_numbers)):
            # Step number (column 0)
            step_item = QTableWidgetItem(str(int(step_numbers[i])))
            step_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(i, 0, step_item)

            # Base shear (column 1)
            shear_item = QTableWidgetItem(f"{base_shears[i]:.2f}")
            shear_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(i, 1, shear_item)

            # Displacement (column 2)
            disp_item = QTableWidgetItem(f"{displacements[i]:.2f}")
            disp_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(i, 2, disp_item)

        # Calculate exact height needed for table content
        self.table.resizeRowsToContents()
        total_height = self.table.horizontalHeader().height()
        for i in range(self.table.rowCount()):
            total_height += self.table.rowHeight(i)
        total_height += 2  # Border
        self.table.setFixedHeight(total_height)

        # Set range BEFORE plotting
        if displacements and base_shears:
            max_disp = max(displacements)
            max_shear = max(base_shears)

            # Disable auto-range
            self.plot_widget.disableAutoRange()

            # Set explicit range from (0,0) with 5% padding
            self.plot_widget.setXRange(0, max_disp * 1.05, padding=0)
            self.plot_widget.setYRange(0, max_shear * 1.05, padding=0)

        # Plot the curve
        pen = pg.mkPen(color='#4a7d89', width=2)
        symbol_brush = pg.mkBrush('#4a7d89')

        self.plot_widget.plot(
            displacements,
            base_shears,
            pen=pen,
            symbol='o',
            symbolSize=8,
            symbolBrush=symbol_brush,
            name=case_name
        )

    def display_all_curves(self, curves_data: list):
        """
        Display multiple pushover curves on a single plot with legend.

        Args:
            curves_data: List of dicts with keys: 'case_name', 'displacements', 'base_shears'
        """
        # Hide table container for all curves view (plot takes full width)
        self.table_container.hide()

        # Clear previous data
        self.table.setRowCount(0)
        self.plot_widget.clear()

        if not curves_data:
            return

        # Define distinct colors for multiple curves
        curve_colors = [
            '#4a7d89',  # Teal (primary accent)
            '#fb923c',  # Orange
            '#3b82f6',  # Blue
            '#2ed573',  # Green
            '#f87171',  # Red
            '#fbbf24',  # Yellow
            '#a78bfa',  # Purple
            '#ec4899',  # Pink
            '#14b8a6',  # Cyan
            '#f59e0b',  # Amber
        ]

        # Track max values for range setting
        max_disp = 0
        max_shear = 0

        # Plot each curve
        for i, curve_data in enumerate(curves_data):
            case_name = curve_data['case_name']
            displacements = curve_data['displacements']
            base_shears = curve_data['base_shears']

            if not displacements or not base_shears:
                continue

            # Update max values
            max_disp = max(max_disp, max(displacements))
            max_shear = max(max_shear, max(base_shears))

            # Use color from palette (cycle if more curves than colors)
            color = curve_colors[i % len(curve_colors)]
            pen = pg.mkPen(color=color, width=2)
            symbol_brush = pg.mkBrush(color)

            # Plot the curve
            self.plot_widget.plot(
                displacements,
                base_shears,
                pen=pen,
                symbol='o',
                symbolSize=6,
                symbolBrush=symbol_brush,
                name=case_name
            )

        # Set range from (0,0) with 5% padding
        if max_disp > 0 and max_shear > 0:
            self.plot_widget.disableAutoRange()
            self.plot_widget.setXRange(0, max_disp * 1.05, padding=0)
            self.plot_widget.setYRange(0, max_shear * 1.05, padding=0)

        # Add legend
        legend = self.plot_widget.addLegend(offset=(10, 10))
        legend.setLabelTextSize('10pt')
        legend.setLabelTextColor('#d1d5db')

    def clear(self):
        """Clear all data from the view."""
        self.table.setRowCount(0)
        self.plot_widget.clear()
        # Show table container again (in case it was hidden)
        self.table_container.show()
