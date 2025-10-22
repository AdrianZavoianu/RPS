"""Results table widget - displays tabular data with GMP styling."""

import pandas as pd
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QFont
from PyQt6.QtWidgets import (QAbstractItemView, QFrame, QHeaderView,
                             QSizePolicy, QTableWidget, QTableWidgetItem,
                             QVBoxLayout, QWidget)


class ResultsTableWidget(QFrame):
    """Table widget for displaying results in tabular format."""

    def __init__(self, parent=None):
        super().__init__(parent)
        # Set size policy: fixed width, expand vertically to match plot height
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Preferred)

        # No border on container - table will have its own border
        self.setObjectName("tableContainer")

        self.setup_ui()

    def setup_ui(self):
        """Setup the table UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)  # No margins - table fills container edge-to-edge
        layout.setSpacing(0)

        self.table = QTableWidget()
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setSortingEnabled(True)

        # Disable scrolling - table should fit all columns
        self.table.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.table.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)

        # Set consistent font across entire table
        table_font = QFont("Inter", 8)
        self.table.setFont(table_font)
        self.table.horizontalHeader().setFont(table_font)

        # Style matching GMP tables
        self.table.setStyleSheet("""
            QTableWidget {
                background-color: #0a0c10;
                border: 1px solid #2c313a;
                border-radius: 6px;
                gridline-color: #2c313a;
                color: #d1d5db;
            }
            QTableWidget::item {
                padding: 3px 4px;
                border: none;
            }
            QTableWidget::item:selected {
                background-color: rgba(74, 125, 137, 0.2);
                color: #4a7d89;
            }
            QTableWidget::item:hover {
                background-color: #161b22;
            }
            QHeaderView::section {
                background-color: #161b22;
                color: #4a7d89;
                padding: 4px 6px;
                border: none;
                border-bottom: 2px solid #2c313a;
                font-weight: 600;
                text-align: center;
            }
            QHeaderView::section:hover {
                background-color: #1f2937;
            }
            QTableWidget QTableCornerButton::section {
                background-color: #161b22;
                border: none;
            }
        """)

        # Configure headers - fixed mode (no resizing)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Fixed)
        self.table.horizontalHeader().setStretchLastSection(False)
        self.table.horizontalHeader().setDefaultAlignment(Qt.AlignmentFlag.AlignCenter)
        self.table.verticalHeader().setVisible(False)
        self.table.setWordWrap(False)  # Prevent wrapping for compact display
        self.table.horizontalHeader().setDefaultSectionSize(55)  # Default column width

        layout.addWidget(self.table)

    def load_data(self, df: pd.DataFrame, result_type: str):
        """Load data from DataFrame into table."""
        if df.empty:
            self.clear_data()
            return

        # Set table dimensions
        self.table.setRowCount(len(df))
        self.table.setColumnCount(len(df.columns))
        self.table.setHorizontalHeaderLabels(df.columns.tolist())

        # Populate data
        for row_idx, (_, row) in enumerate(df.iterrows()):
            for col_idx, value in enumerate(row):
                item = QTableWidgetItem()

                # Format value based on column
                col_name = df.columns[col_idx]

                if col_idx == 0:  # Story column
                    item.setText(str(value))
                    item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                    # Story column styling (use table font)
                else:
                    # Numeric columns
                    try:
                        numeric_value = float(value)
                        # Format based on result type
                        if result_type == "Drifts":
                            # Convert to percentage (multiply by 100)
                            percentage_value = numeric_value * 100
                            formatted = f"{percentage_value:.2f}%"  # 2 decimal places for percentage
                        elif result_type == "Accelerations":
                            formatted = f"{numeric_value:.3f}"  # 3 decimal places for accelerations (g)
                        elif result_type == "Forces":
                            formatted = f"{numeric_value:.2f}"  # 2 decimal places for forces (kN)
                        else:
                            formatted = f"{numeric_value:.3f}"

                        item.setText(formatted)
                        item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)

                        # Color-code based on magnitude and column type
                        if result_type == "Drifts":
                            # Use percentage thresholds
                            percentage = numeric_value * 100

                            # Special styling for Avg, Max, Min columns
                            if col_name in ['Avg', 'Max', 'Min']:
                                # Use consistent table font, just different colors
                                if col_name == 'Max':
                                    # Max column - always show in color based on value
                                    if percentage > 2.0:
                                        item.setForeground(QColor("#e74c3c"))  # Red
                                    elif percentage > 1.0:
                                        item.setForeground(QColor("#f39c12"))  # Orange
                                    else:
                                        item.setForeground(QColor("#2ecc71"))  # Green
                                elif col_name == 'Avg':
                                    item.setForeground(QColor("#4a7d89"))  # Teal accent
                                else:  # Min
                                    item.setForeground(QColor("#7f8b9a"))  # Muted
                            else:
                                # Regular load case columns
                                if percentage > 2.0:
                                    item.setForeground(QColor("#e74c3c"))  # Red
                                elif percentage > 1.0:
                                    item.setForeground(QColor("#f39c12"))  # Orange
                                else:
                                    item.setForeground(QColor("#d1d5db"))  # Default text color

                    except (ValueError, TypeError):
                        item.setText(str(value))
                        item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)

                self.table.setItem(row_idx, col_idx, item)

        # Set column widths - first column (Story) different from data columns
        story_column_width = 70  # Width for Story column
        data_column_width = 55   # Width for data columns (TH01, TH02, Avg, Max, Min, etc.)

        for col_idx in range(len(df.columns)):
            if col_idx == 0:  # First column (Story)
                self.table.setColumnWidth(col_idx, story_column_width)
            else:  # Data columns
                self.table.setColumnWidth(col_idx, data_column_width)

        # Auto-fit container to table content
        # Calculate actual table width needed (columns + small buffer for borders)
        total_width = story_column_width + (len(df.columns) - 1) * data_column_width + 2

        # Set table to this size
        self.table.setMinimumWidth(total_width)
        self.table.setMaximumWidth(total_width)

        # Container matches table width exactly (no extra margins)
        self.setMinimumWidth(total_width)
        self.setMaximumWidth(total_width)

    def clear_data(self):
        """Clear table contents."""
        self.table.setRowCount(0)
        self.table.setColumnCount(0)
