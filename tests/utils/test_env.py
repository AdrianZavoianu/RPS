"""Tests for environment helper utilities."""

import importlib
import pytest


class TestIsDevMode:
    """Tests for is_dev_mode function."""

    def test_returns_false_when_no_env_vars(self, monkeypatch):
        """Should return False when no environment variables are set."""
        monkeypatch.delenv("RPS_ENV", raising=False)
        monkeypatch.delenv("RPS_DEV_MODE", raising=False)

        # Reload module to clear lru_cache
        import utils.env
        importlib.reload(utils.env)

        assert utils.env.is_dev_mode() is False

    @pytest.mark.parametrize("value", ["dev", "development", "1", "true", "yes"])
    def test_returns_true_for_dev_values_rps_env(self, monkeypatch, value):
        """Should return True for various dev values in RPS_ENV."""
        monkeypatch.setenv("RPS_ENV", value)
        monkeypatch.delenv("RPS_DEV_MODE", raising=False)

        import utils.env
        importlib.reload(utils.env)

        assert utils.env.is_dev_mode() is True

    @pytest.mark.parametrize("value", ["dev", "development", "1", "true", "yes"])
    def test_returns_true_for_dev_values_rps_dev_mode(self, monkeypatch, value):
        """Should return True for various dev values in RPS_DEV_MODE."""
        monkeypatch.delenv("RPS_ENV", raising=False)
        monkeypatch.setenv("RPS_DEV_MODE", value)

        import utils.env
        importlib.reload(utils.env)

        assert utils.env.is_dev_mode() is True

    @pytest.mark.parametrize("value", ["DEV", "Development", "TRUE", "Yes"])
    def test_case_insensitive(self, monkeypatch, value):
        """Should be case-insensitive."""
        monkeypatch.setenv("RPS_ENV", value)
        monkeypatch.delenv("RPS_DEV_MODE", raising=False)

        import utils.env
        importlib.reload(utils.env)

        assert utils.env.is_dev_mode() is True

    @pytest.mark.parametrize("value", ["prod", "production", "0", "false", "no", "staging"])
    def test_returns_false_for_non_dev_values(self, monkeypatch, value):
        """Should return False for non-dev values."""
        monkeypatch.setenv("RPS_ENV", value)
        monkeypatch.delenv("RPS_DEV_MODE", raising=False)

        import utils.env
        importlib.reload(utils.env)

        assert utils.env.is_dev_mode() is False

    def test_rps_env_takes_precedence(self, monkeypatch):
        """RPS_ENV should be checked first."""
        monkeypatch.setenv("RPS_ENV", "dev")
        monkeypatch.setenv("RPS_DEV_MODE", "false")  # Would return False if checked

        import utils.env
        importlib.reload(utils.env)

        # RPS_ENV is "dev" so should return True
        assert utils.env.is_dev_mode() is True

    def test_handles_whitespace(self, monkeypatch):
        """Should handle values with whitespace."""
        monkeypatch.setenv("RPS_ENV", "  dev  ")
        monkeypatch.delenv("RPS_DEV_MODE", raising=False)

        import utils.env
        importlib.reload(utils.env)

        assert utils.env.is_dev_mode() is True

    def test_empty_string_returns_false(self, monkeypatch):
        """Should return False for empty string."""
        monkeypatch.setenv("RPS_ENV", "")
        monkeypatch.delenv("RPS_DEV_MODE", raising=False)

        import utils.env
        importlib.reload(utils.env)

        assert utils.env.is_dev_mode() is False
