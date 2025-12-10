"""Global settings manager for RPS application."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from PyQt6.QtCore import QObject, pyqtSignal

logger = logging.getLogger(__name__)

# Default settings
DEFAULT_SETTINGS = {
    "plot_shading_enabled": False,
    "plot_shading_opacity": 0.15,  # 15% opacity for subtle shading
    "layout_borders_enabled": False,  # Show borders between layout zones
}

# Settings file location
SETTINGS_FILE = Path(__file__).parent.parent.parent / "data" / "settings.json"


class SettingsManager(QObject):
    """Singleton manager for global application settings."""

    # Signal emitted when any setting changes
    settings_changed = pyqtSignal(str, object)  # (setting_name, new_value)

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        super().__init__()
        self._initialized = True
        self._settings = DEFAULT_SETTINGS.copy()
        self._load_settings()

    def _load_settings(self):
        """Load settings from file."""
        try:
            if SETTINGS_FILE.exists():
                with open(SETTINGS_FILE, "r") as f:
                    saved = json.load(f)
                    # Merge with defaults (in case new settings were added)
                    for key, value in saved.items():
                        if key in DEFAULT_SETTINGS:
                            self._settings[key] = value
                logger.debug("Settings loaded from %s", SETTINGS_FILE)
        except Exception as e:
            logger.warning("Failed to load settings: %s", e)

    def _save_settings(self):
        """Save settings to file."""
        try:
            SETTINGS_FILE.parent.mkdir(parents=True, exist_ok=True)
            with open(SETTINGS_FILE, "w") as f:
                json.dump(self._settings, f, indent=2)
            logger.debug("Settings saved to %s", SETTINGS_FILE)
        except Exception as e:
            logger.warning("Failed to save settings: %s", e)

    def get(self, key: str, default: Any = None) -> Any:
        """Get a setting value."""
        return self._settings.get(key, default)

    def set(self, key: str, value: Any):
        """Set a setting value and emit change signal."""
        if key in self._settings and self._settings[key] != value:
            self._settings[key] = value
            self._save_settings()
            self.settings_changed.emit(key, value)

    @property
    def plot_shading_enabled(self) -> bool:
        """Whether plot shading is enabled."""
        return self._settings.get("plot_shading_enabled", False)

    @plot_shading_enabled.setter
    def plot_shading_enabled(self, value: bool):
        self.set("plot_shading_enabled", value)

    @property
    def plot_shading_opacity(self) -> float:
        """Opacity for plot shading (0.0 - 1.0)."""
        return self._settings.get("plot_shading_opacity", 0.15)

    @plot_shading_opacity.setter
    def plot_shading_opacity(self, value: float):
        self.set("plot_shading_opacity", max(0.0, min(1.0, value)))

    @property
    def layout_borders_enabled(self) -> bool:
        """Whether layout borders are shown."""
        return self._settings.get("layout_borders_enabled", False)

    @layout_borders_enabled.setter
    def layout_borders_enabled(self, value: bool):
        self.set("layout_borders_enabled", value)


# Global instance
settings = SettingsManager()
