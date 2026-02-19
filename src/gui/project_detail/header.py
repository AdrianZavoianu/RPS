"""Header bar component for project detail window."""

from __future__ import annotations

from typing import Optional, Callable

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QWidget, QHBoxLayout, QLabel, QPushButton

from gui.styles import COLORS
from gui.icon_utils import get_colored_icon_pixmap, create_settings_icon
from gui.ui_helpers import create_styled_label


class ProjectHeader(QWidget):
    """Composable header widget for project detail view."""

    def __init__(
        self,
        project_name: str,
        *,
        on_switch_context,
        on_load_nltha,
        on_load_time_series=None,
        on_create_comparison,
        on_export_nltha,
        on_load_pushover_curves,
        on_load_pushover_results,
        on_export_pushover,
        on_export_project,
        on_settings,
        on_open_reporting=None,
        on_open_pushover_reporting=None,
    ):
        super().__init__()
        self.setObjectName("projectHeader")
        self.setFixedHeight(36)
        self.setStyleSheet(
            f"""
            QWidget#projectHeader {{
                background-color: {COLORS['background']};
                border: none;
                min-height: 36px;
                max-height: 36px;
            }}
        """
        )

        self._on_switch_context = on_switch_context
        self._on_settings = on_settings
        self._active_context = "NLTHA"
        self._context_menu_expanded = False

        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 4, 12, 4)
        layout.setSpacing(6)

        icon_label = QLabel()
        icon_pixmap = get_colored_icon_pixmap("RPS_icon", "#5a9daa", size=32)
        icon_label.setPixmap(icon_pixmap)
        icon_label.setFixedSize(32, 32)
        layout.addWidget(icon_label)

        title = create_styled_label(project_name, "header")
        title.setStyleSheet("font-size: 22px; font-weight: 600;")
        layout.addWidget(title)

        layout.addStretch()

        # Tabs
        self.nltha_tab = self._create_tab_button("NLTHA", active=True)
        self.pushover_tab = self._create_tab_button("Pushover", active=False)
        layout.addWidget(self.nltha_tab)
        layout.addWidget(self.pushover_tab)

        self._context_left_separator = self._create_separator()
        layout.addWidget(self._context_left_separator)

        # NLTHA buttons
        self.nltha_buttons: list[QPushButton] = []
        load_data_btn = self._create_text_link_button("Load NLTHA Data")
        load_data_btn.setToolTip("Import NLTHA data from folder")
        load_data_btn.clicked.connect(on_load_nltha)
        layout.addWidget(load_data_btn)
        self.nltha_buttons.append(load_data_btn)

        if on_load_time_series:
            load_ts_btn = self._create_text_link_button("Load Time Series")
            load_ts_btn.setToolTip("Import time history data for animated visualization")
            load_ts_btn.clicked.connect(on_load_time_series)
            layout.addWidget(load_ts_btn)
            self.nltha_buttons.append(load_ts_btn)

        create_comparison_btn = self._create_text_link_button("Create Comparison")
        create_comparison_btn.setToolTip("Create a new comparison set")
        create_comparison_btn.clicked.connect(on_create_comparison)
        layout.addWidget(create_comparison_btn)
        self.nltha_buttons.append(create_comparison_btn)

        export_nltha_btn = self._create_text_link_button("Export Results")
        export_nltha_btn.setToolTip("Export NLTHA results to file")
        export_nltha_btn.clicked.connect(on_export_nltha)
        layout.addWidget(export_nltha_btn)
        self.nltha_buttons.append(export_nltha_btn)

        if on_open_reporting:
            reporting_btn = self._create_text_link_button("Reporting")
            reporting_btn.setToolTip("Generate PDF reports")
            reporting_btn.clicked.connect(on_open_reporting)
            layout.addWidget(reporting_btn)
            self.nltha_buttons.append(reporting_btn)

        # Pushover buttons
        self.pushover_buttons: list[QPushButton] = []
        load_pushover_btn = self._create_text_link_button("Load Pushover Curves")
        load_pushover_btn.setToolTip("Import pushover capacity curves")
        load_pushover_btn.clicked.connect(on_load_pushover_curves)
        layout.addWidget(load_pushover_btn)
        load_pushover_btn.hide()
        self.pushover_buttons.append(load_pushover_btn)

        load_results_btn = self._create_text_link_button("Load Results")
        load_results_btn.setToolTip("Import pushover global results (drifts, displacements, forces)")
        load_results_btn.clicked.connect(on_load_pushover_results)
        layout.addWidget(load_results_btn)
        load_results_btn.hide()
        self.pushover_buttons.append(load_results_btn)

        export_pushover_btn = self._create_text_link_button("Export Results")
        export_pushover_btn.setToolTip("Export pushover results to file")
        export_pushover_btn.clicked.connect(on_export_pushover)
        layout.addWidget(export_pushover_btn)
        export_pushover_btn.hide()
        self.pushover_buttons.append(export_pushover_btn)

        if on_open_pushover_reporting:
            pushover_reporting_btn = self._create_text_link_button("Reporting")
            pushover_reporting_btn.setToolTip("Generate PDF reports for Pushover results")
            pushover_reporting_btn.clicked.connect(on_open_pushover_reporting)
            layout.addWidget(pushover_reporting_btn)
            pushover_reporting_btn.hide()
            self.pushover_buttons.append(pushover_reporting_btn)

        self._context_right_separator = self._create_separator()
        layout.addWidget(self._context_right_separator)

        export_project_btn = self._create_text_link_button("Export Project")
        export_project_btn.setToolTip("Export complete project to Excel")
        export_project_btn.clicked.connect(on_export_project)
        layout.addWidget(export_project_btn)

        settings_btn = self._create_icon_button(callback=on_settings)
        settings_btn.setToolTip("Settings")
        layout.addWidget(settings_btn)
        self.settings_button = settings_btn

        self._update_context_buttons()
        self._update_tab_styling()

    def set_context(self, context: str) -> None:
        """Update tab/button visibility based on active context."""
        self._active_context = context
        is_nltha = context == "NLTHA"
        self.nltha_tab.setChecked(is_nltha)
        self.pushover_tab.setChecked(not is_nltha)

        self._update_context_buttons()

        self._update_tab_styling()

    def _on_tab_clicked(self, context: str) -> None:
        if context == self._active_context:
            self._context_menu_expanded = not self._context_menu_expanded
            # Keep the active tab checked even when toggling the menu.
            self.nltha_tab.setChecked(self._active_context == "NLTHA")
            self.pushover_tab.setChecked(self._active_context == "Pushover")
            self._update_context_buttons()
            self._update_tab_styling()
            return

        self._context_menu_expanded = True
        self._on_switch_context(context)

    def _create_separator(self) -> QWidget:
        sep = QWidget()
        sep.setFixedWidth(1)
        sep.setStyleSheet(f"background-color: {COLORS['border']};")
        return sep

    def _create_icon_button(self, callback) -> QWidget:
        btn = QPushButton()
        btn.setIcon(create_settings_icon(18, COLORS["muted"]))
        btn.setFixedSize(28, 28)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setStyleSheet(
            f"""
            QPushButton {{
                background-color: transparent;
                border: none;
                border-radius: 4px;
                padding: 4px;
            }}
            QPushButton:hover {{
                background-color: {COLORS['hover']};
            }}
        """
        )
        btn.clicked.connect(callback)
        return btn

    def _create_tab_button(self, text: str, active: bool = False) -> QPushButton:
        from gui.ui_helpers import create_tab_button

        btn = create_tab_button(text, active=active)
        btn.clicked.connect(lambda: self._on_tab_clicked(text))
        return btn

    def _create_text_link_button(self, text: str) -> QPushButton:
        from gui.ui_helpers import create_text_link_button

        btn = create_text_link_button(text)
        btn.setStyleSheet(
            f"""
            QPushButton {{
                background-color: transparent;
                color: {COLORS['text']};
                border: none;
                padding: 4px 10px;
                font-size: 15px;
                font-weight: 500;
                letter-spacing: 0.3px;
            }}
            QPushButton:hover {{
                color: {COLORS['accent']};
                background-color: transparent;
            }}
            QPushButton:pressed {{
                color: {COLORS['accent']};
                background-color: transparent;
            }}
        """
        )
        return btn

    def _update_context_buttons(self) -> None:
        show_nltha = self._context_menu_expanded and self._active_context == "NLTHA"
        show_pushover = self._context_menu_expanded and self._active_context == "Pushover"

        for btn in self.nltha_buttons:
            btn.setVisible(show_nltha)
        for btn in self.pushover_buttons:
            btn.setVisible(show_pushover)

        show_separators = self._context_menu_expanded
        self._context_left_separator.setVisible(show_separators)
        self._context_right_separator.setVisible(show_separators)

    def _update_tab_styling(self) -> None:
        """Restyle tabs to reflect the active context."""
        for tab_btn in [self.nltha_tab, self.pushover_tab]:
            is_active = tab_btn.isChecked()
            tab_btn.setStyleSheet(
                f"""
                QPushButton {{
                    background-color: transparent;
                    color: {COLORS['muted'] if not is_active else COLORS['accent']};
                    border: none;
                    border-bottom: 2px solid {'transparent' if not is_active else COLORS['accent']};
                    border-radius: 0px;
                    padding: 4px 16px;
                    font-size: 15px;
                    font-weight: 500;
                    letter-spacing: 0.3px;
                }}
                QPushButton:hover {{
                    color: {COLORS['text'] if not is_active else COLORS['accent']};
                    background-color: transparent;
                }}
                QPushButton:checked {{
                    color: {COLORS['accent']};
                    border-bottom: 2px solid {COLORS['accent']};
                    border-radius: 0px;
                    font-weight: 500;
                }}
            """
            )
