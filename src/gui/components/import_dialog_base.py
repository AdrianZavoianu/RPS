"""Base class for import dialogs with shared patterns.

Provides common functionality for:
- Progress tracking with worker threads
- Folder/file selection UI
- Log area for status messages
- Styled buttons and layouts
- Load case checkbox lists
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional, Set, List

from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QColor, QPainter, QPen, QPixmap, QIcon
from PyQt6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QProgressBar,
    QTextEdit,
    QScrollArea,
    QWidget,
    QGroupBox,
    QListWidget,
    QListWidgetItem,
    QFileDialog,
    QMessageBox,
    QApplication,
)

from ..styles import COLORS
from ..ui_helpers import create_styled_button, create_styled_label

logger = logging.getLogger(__name__)


def create_checkbox_icons() -> tuple[QIcon, QIcon]:
    """Create checkbox icons for unchecked and checked states."""
    size = 20

    # Unchecked icon (empty)
    unchecked_pixmap = QPixmap(size, size)
    unchecked_pixmap.fill(Qt.GlobalColor.transparent)
    unchecked_icon = QIcon(unchecked_pixmap)

    # Checked icon (with checkmark)
    checked_pixmap = QPixmap(size, size)
    checked_pixmap.fill(Qt.GlobalColor.transparent)

    painter = QPainter(checked_pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)

    # Draw checkmark
    painter.setPen(QPen(QColor("#ffffff"), 2.5, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
    painter.drawLine(int(size * 0.25), int(size * 0.5), int(size * 0.4), int(size * 0.65))
    painter.drawLine(int(size * 0.4), int(size * 0.65), int(size * 0.75), int(size * 0.3))

    painter.end()
    checked_icon = QIcon(checked_pixmap)

    return unchecked_icon, checked_icon


class BaseImportWorker(QThread):
    """Base class for import worker threads.
    
    Subclasses should implement run() and emit appropriate signals.
    """
    
    progress = pyqtSignal(str, int, int)  # message, current, total
    finished = pyqtSignal(object)  # result (dict or other)
    error = pyqtSignal(str)  # error message
    
    def __init__(self, parent=None):
        super().__init__(parent)
    
    def _emit_progress(self, message: str, current: int, total: int) -> None:
        """Helper to emit progress signal."""
        self.progress.emit(message, current, total)


class ImportDialogBase(QDialog):
    """Base class for import dialogs with common UI patterns.
    
    Subclasses must implement:
    - _setup_specific_ui(): Add dialog-specific UI elements
    - _on_browse(): Handle folder/file selection
    - _start_import(): Begin the import process
    
    Note: ABC is not used due to PyQt6 metaclass conflicts.
    Abstract methods raise NotImplementedError if not overridden.
    """
    
    import_completed = pyqtSignal(int)  # Emits result_set_id on success
    
    def __init__(
        self,
        parent: Optional[QWidget] = None,
        title: str = "Import Data",
        min_width: int = 700,
        min_height: int = 500,
    ):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setMinimumSize(min_width, min_height)
        
        # Common state
        self._worker: Optional[QThread] = None
        self._is_importing = False
        
        # Create checkbox icons
        self._unchecked_icon, self._checked_icon = create_checkbox_icons()
        
        self._setup_base_ui()
        self._setup_specific_ui()
        self._apply_styles()
    
    def _setup_base_ui(self) -> None:
        """Set up common UI elements."""
        self._main_layout = QVBoxLayout(self)
        self._main_layout.setSpacing(16)
        self._main_layout.setContentsMargins(24, 24, 24, 24)
    
    def _setup_specific_ui(self) -> None:
        """Set up dialog-specific UI elements. Must be implemented by subclasses."""
        raise NotImplementedError("Subclasses must implement _setup_specific_ui()")
    
    def _create_folder_section(self, label_text: str = "Folder:") -> tuple[QLineEdit, QWidget]:
        """Create a folder selection section with browse button.
        
        Returns: (path_edit, container_widget)
        """
        container = QWidget()
        layout = QHBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        
        label = create_styled_label(label_text)
        label.setFixedWidth(60)
        layout.addWidget(label)
        
        path_edit = QLineEdit()
        path_edit.setReadOnly(True)
        path_edit.setPlaceholderText("Select a folder...")
        layout.addWidget(path_edit, stretch=1)
        
        browse_btn = create_styled_button("Browse...", variant="secondary")
        browse_btn.clicked.connect(self._on_browse)
        layout.addWidget(browse_btn)
        
        return path_edit, container
    
    def _create_progress_section(self) -> tuple[QProgressBar, QTextEdit, QWidget]:
        """Create a progress section with progress bar and log area.
        
        Returns: (progress_bar, log_text, container_widget)
        """
        group = QGroupBox("Progress")
        group.setStyleSheet(self._get_group_box_style())
        layout = QVBoxLayout(group)
        layout.setSpacing(8)
        
        progress_bar = QProgressBar()
        progress_bar.setRange(0, 100)
        progress_bar.setValue(0)
        progress_bar.setTextVisible(True)
        progress_bar.setStyleSheet(self._get_progress_bar_style())
        layout.addWidget(progress_bar)
        
        log_text = QTextEdit()
        log_text.setReadOnly(True)
        log_text.setMaximumHeight(120)
        log_text.setStyleSheet(self._get_log_text_style())
        layout.addWidget(log_text)
        
        return progress_bar, log_text, group
    
    def _create_load_case_list(self, title: str = "Load Cases") -> tuple[QListWidget, QWidget]:
        """Create a scrollable load case checkbox list.
        
        Returns: (list_widget, container_widget)
        """
        group = QGroupBox(title)
        group.setStyleSheet(self._get_group_box_style())
        layout = QVBoxLayout(group)
        
        # Select all / Clear buttons
        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)
        
        select_all_btn = create_styled_button("Select All", variant="ghost")
        select_all_btn.clicked.connect(lambda: self._select_all_load_cases(True))
        btn_row.addWidget(select_all_btn)
        
        clear_btn = create_styled_button("Clear", variant="ghost")
        clear_btn.clicked.connect(lambda: self._select_all_load_cases(False))
        btn_row.addWidget(clear_btn)
        
        btn_row.addStretch()
        layout.addLayout(btn_row)
        
        # Scroll area with list
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet(f"""
            QScrollArea {{
                border: 1px solid {COLORS['border']};
                border-radius: 6px;
                background-color: {COLORS['card']};
            }}
        """)
        
        list_widget = QListWidget()
        list_widget.setStyleSheet(self._get_list_widget_style())
        scroll.setWidget(list_widget)
        
        layout.addWidget(scroll, stretch=1)
        
        # Store reference for select all
        self._load_case_list = list_widget
        
        return list_widget, group
    
    def _create_button_row(self) -> tuple[QWidget, QWidget, QWidget]:
        """Create the bottom button row with Cancel and Import buttons.
        
        Returns: (cancel_btn, import_btn, container_widget)
        """
        container = QWidget()
        layout = QHBoxLayout(container)
        layout.setContentsMargins(0, 16, 0, 0)
        layout.addStretch()
        
        cancel_btn = create_styled_button("Cancel", variant="secondary")
        cancel_btn.clicked.connect(self._on_cancel)
        layout.addWidget(cancel_btn)
        
        import_btn = create_styled_button("Import", variant="primary")
        import_btn.clicked.connect(self._start_import)
        import_btn.setEnabled(False)
        layout.addWidget(import_btn)
        
        return cancel_btn, import_btn, container
    
    def _select_all_load_cases(self, select: bool) -> None:
        """Select or deselect all load cases in the list."""
        if not hasattr(self, '_load_case_list'):
            return
        
        for i in range(self._load_case_list.count()):
            item = self._load_case_list.item(i)
            item.setCheckState(Qt.CheckState.Checked if select else Qt.CheckState.Unchecked)
    
    def _get_selected_load_cases(self) -> Set[str]:
        """Get the set of selected load case names."""
        if not hasattr(self, '_load_case_list'):
            return set()
        
        selected = set()
        for i in range(self._load_case_list.count()):
            item = self._load_case_list.item(i)
            if item.checkState() == Qt.CheckState.Checked:
                selected.add(item.text())
        return selected
    
    def _populate_load_case_list(self, load_cases: List[str], check_all: bool = True) -> None:
        """Populate the load case list with items."""
        if not hasattr(self, '_load_case_list'):
            return
        
        self._load_case_list.clear()
        for lc in sorted(load_cases):
            item = QListWidgetItem(lc)
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            item.setCheckState(Qt.CheckState.Checked if check_all else Qt.CheckState.Unchecked)
            self._load_case_list.addItem(item)
    
    def _log(self, message: str) -> None:
        """Append a message to the log area."""
        if hasattr(self, '_log_text'):
            self._log_text.append(message)
            # Auto-scroll to bottom
            scrollbar = self._log_text.verticalScrollBar()
            scrollbar.setValue(scrollbar.maximum())
    
    def _update_progress(self, message: str, current: int, total: int) -> None:
        """Update the progress bar and log."""
        if hasattr(self, '_progress_bar') and total > 0:
            percent = int((current / total) * 100)
            self._progress_bar.setValue(percent)
        self._log(message)
    
    def _show_error(self, message: str, title: str = "Import Error") -> None:
        """Show an error message box."""
        QMessageBox.critical(self, title, message)
    
    def _show_success(self, message: str, title: str = "Import Complete") -> None:
        """Show a success message box."""
        QMessageBox.information(self, title, message)
    
    def _on_browse(self) -> None:
        """Handle folder/file browse button click. Must be implemented by subclasses."""
        raise NotImplementedError("Subclasses must implement _on_browse()")
    
    def _start_import(self) -> None:
        """Start the import process. Must be implemented by subclasses."""
        raise NotImplementedError("Subclasses must implement _start_import()")
    
    def _on_cancel(self) -> None:
        """Handle cancel button click."""
        if self._worker and self._worker.isRunning():
            self._worker.terminate()
            self._worker.wait()
        self.reject()
    
    def _on_worker_error(self, error_message: str) -> None:
        """Handle worker thread error."""
        self._is_importing = False
        self._log(f"Error: {error_message}")
        self._show_error(error_message)
        if hasattr(self, '_import_btn'):
            self._import_btn.setEnabled(True)
    
    def _apply_styles(self) -> None:
        """Apply dialog styles."""
        self.setStyleSheet(f"""
            QDialog {{
                background-color: {COLORS['background']};
            }}
        """)
    
    def _get_group_box_style(self) -> str:
        """Get style for group boxes."""
        return f"""
            QGroupBox {{
                font-weight: bold;
                font-size: 13px;
                color: {COLORS['text']};
                border: 1px solid {COLORS['border']};
                border-radius: 8px;
                margin-top: 12px;
                padding-top: 8px;
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                left: 12px;
                padding: 0 6px;
            }}
        """
    
    def _get_progress_bar_style(self) -> str:
        """Get style for progress bars."""
        return f"""
            QProgressBar {{
                border: 1px solid {COLORS['border']};
                border-radius: 4px;
                background-color: {COLORS['card']};
                text-align: center;
                color: {COLORS['text']};
                height: 20px;
            }}
            QProgressBar::chunk {{
                background-color: {COLORS['accent']};
                border-radius: 3px;
            }}
        """
    
    def _get_log_text_style(self) -> str:
        """Get style for log text areas."""
        return f"""
            QTextEdit {{
                background-color: {COLORS['card']};
                color: {COLORS['text']};
                border: 1px solid {COLORS['border']};
                border-radius: 4px;
                font-family: 'Consolas', 'Monaco', monospace;
                font-size: 11px;
                padding: 8px;
            }}
        """
    
    def _get_list_widget_style(self) -> str:
        """Get style for list widgets."""
        return f"""
            QListWidget {{
                background-color: {COLORS['card']};
                color: {COLORS['text']};
                border: none;
                outline: none;
            }}
            QListWidget::item {{
                padding: 6px 8px;
                border-radius: 4px;
            }}
            QListWidget::item:hover {{
                background-color: {COLORS['hover']};
            }}
            QListWidget::item:selected {{
                background-color: {COLORS['accent']};
                color: white;
            }}
        """
