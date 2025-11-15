"""Dialog for creating a new comparison set."""

from PyQt6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QGroupBox,
    QCheckBox,
    QScrollArea,
    QWidget,
    QMessageBox,
)
from PyQt6.QtCore import Qt

from gui.design_tokens import FormStyles, PALETTE
from gui.styles import COLORS
from gui.ui_helpers import create_styled_button, create_styled_label


class ComparisonSetDialog(QDialog):
    """Dialog to create a new comparison set by selecting result sets and result types."""

    def __init__(self, project_id: int, result_sets: list, session, parent=None):
        super().__init__(parent)
        self.project_id = project_id
        self.result_sets = result_sets  # List of ResultSet objects
        self.session = session

        # Get available result types from the database
        result_set_ids = [rs.id for rs in result_sets]
        self.global_result_types = self._get_available_global_types(result_set_ids)
        self.element_result_types = self._get_available_element_types(result_set_ids)
        self.joint_result_types = self._get_available_joint_types(result_set_ids)

        # Selected items
        self.selected_result_set_ids = []
        self.selected_result_types = []

        # Checkboxes
        self.result_set_checkboxes = {}
        self.result_type_checkboxes = {}

        self.setWindowTitle("Create Comparison Set")
        self.setModal(True)
        # Wide-oriented like folder import
        self.setMinimumSize(1200, 650)
        self.resize(1400, 700)

        self.setStyleSheet(FormStyles.dialog())
        self._setup_ui()

    def _setup_ui(self):
        """Create dialog layout."""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(16, 8, 16, 16)
        main_layout.setSpacing(12)

        # Header with larger font
        header = create_styled_label("Create Comparison Set", "header")
        header.setStyleSheet(f"color: {COLORS['text']}; font-size: 24px; font-weight: 600;")
        main_layout.addWidget(header)

        # ============ TOP ROW: Name and Description ============
        config_row = QHBoxLayout()
        config_row.setSpacing(8)

        # Name input - stretch=1 to align with Result Sets column
        name_group = QGroupBox("Comparison Set Name")
        name_group.setStyleSheet(self._groupbox_style())
        name_layout = QVBoxLayout(name_group)
        name_layout.setContentsMargins(8, 8, 8, 8)

        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("e.g., COM1, COM2, DES-MCE-Comparison...")
        self.name_input.setStyleSheet(self._entry_style())
        name_layout.addWidget(self.name_input)
        config_row.addWidget(name_group, stretch=1)

        # Description input - stretch=3 to align with Result Types column
        desc_group = QGroupBox("Description (optional)")
        desc_group.setStyleSheet(self._groupbox_style())
        desc_layout = QVBoxLayout(desc_group)
        desc_layout.setContentsMargins(8, 8, 8, 8)

        self.desc_input = QLineEdit()
        self.desc_input.setPlaceholderText("e.g., Comparison of DES and MCE results...")
        self.desc_input.setStyleSheet(self._entry_style())
        desc_layout.addWidget(self.desc_input)
        config_row.addWidget(desc_group, stretch=3)

        main_layout.addLayout(config_row)

        # ============ MIDDLE ROW: Result Sets | Result Types ============
        data_row = QHBoxLayout()
        data_row.setSpacing(8)

        # Result Sets Selection
        result_sets_group = QGroupBox("Result Sets to Compare")
        result_sets_group.setStyleSheet(self._groupbox_style())
        result_sets_layout = QVBoxLayout()
        result_sets_layout.setContentsMargins(8, 12, 8, 8)
        result_sets_layout.setSpacing(4)

        # Quick actions for result sets
        rs_actions_layout = QHBoxLayout()
        select_all_rs_btn = create_styled_button("All", "ghost", "sm")
        select_all_rs_btn.clicked.connect(self._select_all_result_sets)
        deselect_all_rs_btn = create_styled_button("None", "ghost", "sm")
        deselect_all_rs_btn.clicked.connect(self._deselect_all_result_sets)
        rs_actions_layout.addWidget(select_all_rs_btn)
        rs_actions_layout.addWidget(deselect_all_rs_btn)
        rs_actions_layout.addStretch()
        result_sets_layout.addLayout(rs_actions_layout)

        # Scrollable result sets
        rs_scroll = QScrollArea()
        rs_scroll.setWidgetResizable(True)
        rs_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        rs_scroll.setStyleSheet(FormStyles.scroll_area())

        rs_container = QWidget()
        rs_container_layout = QVBoxLayout(rs_container)
        rs_container_layout.setContentsMargins(4, 4, 4, 4)
        rs_container_layout.setSpacing(0)

        # Create checkboxes for each result set
        for result_set in self.result_sets:
            checkbox = QCheckBox(f"{result_set.name}")
            checkbox.setStyleSheet(self._checkbox_style())
            checkbox.setChecked(True)  # Default: all selected
            checkbox.stateChanged.connect(self._update_selections)
            self.result_set_checkboxes[result_set.id] = checkbox
            rs_container_layout.addWidget(checkbox)

        rs_container_layout.addStretch()
        rs_scroll.setWidget(rs_container)
        result_sets_layout.addWidget(rs_scroll)

        result_sets_group.setLayout(result_sets_layout)
        # Reduce width to align with name field (stretch=1)
        data_row.addWidget(result_sets_group, stretch=1)

        # Result Types Selection
        result_types_group = QGroupBox("Result Types to Include")
        result_types_group.setStyleSheet(self._groupbox_style())
        result_types_layout = QVBoxLayout()
        result_types_layout.setContentsMargins(8, 12, 8, 8)
        result_types_layout.setSpacing(4)

        # Quick actions for result types
        rt_actions_layout = QHBoxLayout()
        select_all_rt_btn = create_styled_button("All", "ghost", "sm")
        select_all_rt_btn.clicked.connect(self._select_all_result_types)
        deselect_all_rt_btn = create_styled_button("None", "ghost", "sm")
        deselect_all_rt_btn.clicked.connect(self._deselect_all_result_types)
        rt_actions_layout.addWidget(select_all_rt_btn)
        rt_actions_layout.addWidget(deselect_all_rt_btn)
        rt_actions_layout.addStretch()
        result_types_layout.addLayout(rt_actions_layout)

        # Three-column layout for result types (no scrolling, no border)
        rt_columns_widget = QWidget()
        rt_columns_widget.setStyleSheet(f"""
            QWidget {{
                background-color: transparent;
            }}
        """)
        rt_columns_layout = QHBoxLayout(rt_columns_widget)
        rt_columns_layout.setContentsMargins(4, 4, 4, 4)
        rt_columns_layout.setSpacing(24)

        # Column 1: Global Results (only show if available)
        if self.global_result_types:
            global_column = QVBoxLayout()
            global_column.setSpacing(0)
            global_label = QLabel("Global Results:")
            global_label.setStyleSheet(f"color: {COLORS['accent']}; font-size: 13px; font-weight: 600; padding: 4px 0px;")
            global_column.addWidget(global_label)

            for result_type in self.global_result_types:
                checkbox = QCheckBox(result_type)
                checkbox.setStyleSheet(self._checkbox_style(indent=False))
                checkbox.setChecked(True)
                checkbox.stateChanged.connect(self._update_selections)
                self.result_type_checkboxes[result_type] = checkbox
                global_column.addWidget(checkbox)

            global_column.addStretch()
            rt_columns_layout.addLayout(global_column)

        # Column 2: Element Results (only show if available)
        if self.element_result_types:
            element_column = QVBoxLayout()
            element_column.setSpacing(0)
            element_label = QLabel("Element Results:")
            element_label.setStyleSheet(f"color: {COLORS['accent']}; font-size: 13px; font-weight: 600; padding: 4px 0px;")
            element_column.addWidget(element_label)

            for result_type in self.element_result_types:
                checkbox = QCheckBox(result_type)
                checkbox.setStyleSheet(self._checkbox_style(indent=False))
                checkbox.setChecked(True)
                checkbox.stateChanged.connect(self._update_selections)
                self.result_type_checkboxes[result_type] = checkbox
                element_column.addWidget(checkbox)

            element_column.addStretch()
            rt_columns_layout.addLayout(element_column)

        # Column 3: Joint Results (only show if available)
        if self.joint_result_types:
            joint_column = QVBoxLayout()
            joint_column.setSpacing(0)
            joint_label = QLabel("Joint Results:")
            joint_label.setStyleSheet(f"color: {COLORS['accent']}; font-size: 13px; font-weight: 600; padding: 4px 0px;")
            joint_column.addWidget(joint_label)

            for result_type in self.joint_result_types:
                checkbox = QCheckBox(result_type)
                checkbox.setStyleSheet(self._checkbox_style(indent=False))
                checkbox.setChecked(True)
                checkbox.stateChanged.connect(self._update_selections)
                self.result_type_checkboxes[result_type] = checkbox
                joint_column.addWidget(checkbox)

            joint_column.addStretch()
            rt_columns_layout.addLayout(joint_column)

        result_types_layout.addWidget(rt_columns_widget)

        result_types_group.setLayout(result_types_layout)
        # Increase width to fill space (stretch=3 to align with name+desc span of 1+2=3)
        data_row.addWidget(result_types_group, stretch=3)

        main_layout.addLayout(data_row, stretch=1)

        # ============ BOTTOM ROW: Buttons ============
        button_layout = QHBoxLayout()
        button_layout.setSpacing(12)
        button_layout.addStretch()

        self.cancel_btn = create_styled_button("Cancel", "ghost")
        self.cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(self.cancel_btn)

        self.create_btn = create_styled_button("Create Comparison Set", "primary")
        self.create_btn.clicked.connect(self._validate_and_accept)
        button_layout.addWidget(self.create_btn)

        main_layout.addLayout(button_layout)

        # Initialize selections
        self._update_selections()

    @staticmethod
    def _groupbox_style() -> str:
        return FormStyles.group_box()

    @staticmethod
    def _entry_style() -> str:
        c = PALETTE
        return f"""
            QLineEdit {{
                background-color: {c['bg_tertiary']};
                border: 1px solid {c['border_default']};
                border-radius: 6px;
                padding: 8px 12px;
                color: {c['text_primary']};
            }}
            QLineEdit:focus {{
                border-color: {c['accent_primary']};
            }}
        """

    @staticmethod
    def _checkbox_style(indent: bool = False) -> str:
        return FormStyles.checkbox(indent=indent)

    def _select_all_result_sets(self):
        """Select all result set checkboxes."""
        for checkbox in self.result_set_checkboxes.values():
            checkbox.setChecked(True)

    def _deselect_all_result_sets(self):
        """Deselect all result set checkboxes."""
        for checkbox in self.result_set_checkboxes.values():
            checkbox.setChecked(False)

    def _select_all_result_types(self):
        """Select all result type checkboxes."""
        for checkbox in self.result_type_checkboxes.values():
            checkbox.setChecked(True)

    def _deselect_all_result_types(self):
        """Deselect all result type checkboxes."""
        for checkbox in self.result_type_checkboxes.values():
            checkbox.setChecked(False)

    def _get_available_global_types(self, result_set_ids: list) -> list:
        """Get available global result types from cache."""
        from database.models import GlobalResultsCache

        # Query distinct result types for these result sets
        available = self.session.query(GlobalResultsCache.result_type)\
            .filter(GlobalResultsCache.result_set_id.in_(result_set_ids))\
            .distinct()\
            .all()

        types = [row[0] for row in available]

        # Map cache names to display names and maintain order
        type_map = {
            'Drifts': 'Drifts',
            'Accelerations': 'Accelerations',
            'Forces': 'Forces',
            'Displacements': 'Displacements',
        }

        return [display for cache, display in type_map.items() if cache in types]

    def _get_available_element_types(self, result_set_ids: list) -> list:
        """Get available element result types from cache."""
        from database.models import ElementResultsCache

        # Query distinct result types for these result sets
        available = self.session.query(ElementResultsCache.result_type)\
            .filter(ElementResultsCache.result_set_id.in_(result_set_ids))\
            .distinct()\
            .all()

        types = [row[0] for row in available]

        # Extract base types (remove direction suffixes like _V22, _V33)
        base_types = set()
        for t in types:
            # Split on underscore and take first part (e.g., 'WallShears_V22' -> 'WallShears')
            base = t.split('_')[0]
            base_types.add(base)

        # Map cache names to display names and maintain order
        type_map = {
            'WallShears': 'WallShears',
            'QuadRotations': 'QuadRotations',
            'ColumnShears': 'ColumnShears',
            'ColumnAxials': 'ColumnAxials',
            'ColumnRotations': 'ColumnRotations',
            'BeamRotations': 'BeamRotations',
        }

        return [display for cache, display in type_map.items() if cache in base_types]

    def _get_available_joint_types(self, result_set_ids: list) -> list:
        """Get available joint result types from cache."""
        from database.models import JointResultsCache

        # Query distinct result types for these result sets
        available = self.session.query(JointResultsCache.result_type)\
            .filter(JointResultsCache.result_set_id.in_(result_set_ids))\
            .distinct()\
            .all()

        types = [row[0] for row in available]

        # Extract base types (remove suffixes like _Min)
        base_types = set()
        for t in types:
            # Split on underscore and take first part (e.g., 'SoilPressures_Min' -> 'SoilPressures')
            base = t.split('_')[0]
            base_types.add(base)

        # Map cache names to display names and maintain order
        type_map = {
            'SoilPressures': 'SoilPressures',
            'VerticalDisplacements': 'VerticalDisplacements',
        }

        return [display for cache, display in type_map.items() if cache in base_types]

    def _update_selections(self):
        """Update selected result sets and result types."""
        # Update selected result set IDs
        self.selected_result_set_ids = [
            rs_id for rs_id, checkbox in self.result_set_checkboxes.items()
            if checkbox.isChecked()
        ]

        # Update selected result types
        self.selected_result_types = [
            rt for rt, checkbox in self.result_type_checkboxes.items()
            if checkbox.isChecked()
        ]

    def _validate_and_accept(self):
        """Validate inputs and accept dialog."""
        name = self.name_input.text().strip()

        if not name:
            QMessageBox.warning(
                self,
                "Invalid Input",
                "Please enter a name for the comparison set."
            )
            return

        if len(self.selected_result_set_ids) < 2:
            QMessageBox.warning(
                self,
                "Invalid Selection",
                "Please select at least 2 result sets to compare."
            )
            return

        if len(self.selected_result_types) == 0:
            QMessageBox.warning(
                self,
                "Invalid Selection",
                "Please select at least one result type to include."
            )
            return

        self.accept()

    def get_comparison_data(self):
        """Get the comparison set configuration."""
        return {
            'name': self.name_input.text().strip(),
            'description': self.desc_input.text().strip() or None,
            'result_set_ids': self.selected_result_set_ids,
            'result_types': self.selected_result_types,
        }
