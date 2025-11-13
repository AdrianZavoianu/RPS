"""Blur overlay widget for modal dialogs."""

from PyQt6.QtWidgets import QWidget, QGraphicsBlurEffect
from PyQt6.QtCore import Qt, QRect, QPropertyAnimation, QEasingCurve, pyqtProperty
from PyQt6.QtGui import QPainter, QColor


class BlurOverlay(QWidget):
    """Semi-transparent overlay with blur effect for modal dialogs."""

    def __init__(self, parent=None):
        super().__init__(parent)

        # Make it cover the entire parent
        self.setGeometry(parent.rect() if parent else QRect(0, 0, 800, 600))

        # Enable transparency
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, False)

        # Set stacking order
        self.raise_()

        # Opacity for fade animation
        self._opacity = 0.0

        # Animation
        self.fade_animation = QPropertyAnimation(self, b"opacity")
        self.fade_animation.setDuration(200)
        self.fade_animation.setEasingCurve(QEasingCurve.Type.OutCubic)

    @pyqtProperty(float)
    def opacity(self):
        return self._opacity

    @opacity.setter
    def opacity(self, value):
        self._opacity = value
        self.update()

    def paintEvent(self, event):
        """Draw semi-transparent overlay."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Semi-transparent black overlay (increased opacity for stronger blur)
        overlay_color = QColor(0, 0, 0, int(200 * self._opacity))
        painter.fillRect(self.rect(), overlay_color)

    def show_animated(self):
        """Show overlay with fade-in animation."""
        self.show()
        self.fade_animation.setStartValue(0.0)
        self.fade_animation.setEndValue(1.0)
        self.fade_animation.start()

    def hide_animated(self):
        """Hide overlay with fade-out animation."""
        self.fade_animation.setStartValue(1.0)
        self.fade_animation.setEndValue(0.0)
        self.fade_animation.finished.connect(self.hide)
        self.fade_animation.start()

    def resizeEvent(self, event):
        """Update size when parent is resized."""
        if self.parent():
            self.setGeometry(self.parent().rect())
        super().resizeEvent(event)
