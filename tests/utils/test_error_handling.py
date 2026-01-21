"""Tests for error handling utilities."""

import logging
import pytest
from unittest.mock import MagicMock, patch

from utils.error_handling import (
    format_error_message,
    log_exception,
    handle_worker_error,
    safe_operation,
    ErrorCollector,
)


class TestFormatErrorMessage:
    """Tests for format_error_message function."""

    def test_basic_error_message(self):
        """Test formatting a basic exception."""
        error = ValueError("Invalid value")
        result = format_error_message(error)
        assert result == "ValueError: Invalid value"

    def test_with_context(self):
        """Test formatting with context."""
        error = ValueError("Invalid value")
        result = format_error_message(error, context="Loading data")
        assert result == "Loading data - ValueError: Invalid value"

    def test_without_type(self):
        """Test formatting without exception type."""
        error = ValueError("Invalid value")
        result = format_error_message(error, include_type=False)
        assert result == "Invalid value"

    def test_context_and_no_type(self):
        """Test formatting with context but without type."""
        error = ValueError("Invalid value")
        result = format_error_message(error, context="Loading data", include_type=False)
        assert result == "Loading data - Invalid value"

    def test_empty_error_message(self):
        """Test handling of empty error messages."""
        error = ValueError("")
        result = format_error_message(error)
        assert result == "ValueError"

    def test_none_error_message(self):
        """Test handling of None-like error messages."""
        error = Exception("None")
        result = format_error_message(error)
        assert result == "Exception"

    def test_custom_exception(self):
        """Test formatting custom exception types."""
        class CustomError(Exception):
            pass

        error = CustomError("Custom message")
        result = format_error_message(error)
        assert result == "CustomError: Custom message"


class TestLogException:
    """Tests for log_exception function."""

    def test_logs_error_with_context(self):
        """Test that exception is logged with context."""
        error = ValueError("Test error")

        with patch("utils.error_handling.logger") as mock_logger:
            log_exception(error, "Test context")

            mock_logger.log.assert_called_once()
            call_args = mock_logger.log.call_args
            assert call_args[0][0] == logging.ERROR
            assert "Test context" in call_args[0][1]
            assert "Test error" in call_args[0][1]
            assert call_args[1]["exc_info"] is True

    def test_logs_with_extra_context(self):
        """Test that extra context is included."""
        error = ValueError("Test error")
        extra = {"file_path": "/test/path.xlsx"}

        with patch("utils.error_handling.logger") as mock_logger:
            log_exception(error, "Test context", extra=extra)

            call_args = mock_logger.log.call_args
            assert "file_path" in call_args[1]["extra"]
            assert call_args[1]["extra"]["file_path"] == "/test/path.xlsx"

    def test_logs_with_custom_level(self):
        """Test logging at different levels."""
        error = ValueError("Test error")

        with patch("utils.error_handling.logger") as mock_logger:
            log_exception(error, "Test context", level=logging.WARNING)

            call_args = mock_logger.log.call_args
            assert call_args[0][0] == logging.WARNING

    def test_includes_error_type_in_extra(self):
        """Test that error type is included in extra."""
        error = KeyError("missing_key")

        with patch("utils.error_handling.logger") as mock_logger:
            log_exception(error, "Test context")

            call_args = mock_logger.log.call_args
            assert call_args[1]["extra"]["error_type"] == "KeyError"


class TestHandleWorkerError:
    """Tests for handle_worker_error function."""

    def test_returns_formatted_message(self):
        """Test that it returns a formatted error message."""
        error = ValueError("Invalid data")
        result = handle_worker_error(error, "Import failed")
        assert result == "Import failed - ValueError: Invalid data"

    def test_logs_exception(self):
        """Test that exception is logged."""
        error = ValueError("Invalid data")

        with patch("utils.error_handling.log_exception") as mock_log:
            handle_worker_error(error, "Import failed")
            mock_log.assert_called_once()

    def test_includes_additional_context_in_log(self):
        """Test that additional args are included in log extra."""
        error = ValueError("Invalid data")
        file_path = "/test/file.xlsx"

        with patch("utils.error_handling.log_exception") as mock_log:
            handle_worker_error(error, "Import failed", file_path)

            mock_log.assert_called_once()
            # Check positional args: (error, context, extra_dict)
            call_args = mock_log.call_args
            extra = call_args[0][2] if len(call_args[0]) > 2 else call_args.kwargs.get("extra", {})
            assert "context_0" in extra
            assert extra["context_0"] == file_path

    def test_handles_multiple_context_args(self):
        """Test handling multiple additional context arguments."""
        error = ValueError("Invalid data")

        with patch("utils.error_handling.log_exception") as mock_log:
            handle_worker_error(error, "Import failed", "arg1", "arg2", "arg3")

            mock_log.assert_called_once()
            call_args = mock_log.call_args
            extra = call_args[0][2] if len(call_args[0]) > 2 else call_args.kwargs.get("extra", {})
            assert extra["context_0"] == "arg1"
            assert extra["context_1"] == "arg2"
            assert extra["context_2"] == "arg3"


class TestSafeOperation:
    """Tests for safe_operation function."""

    def test_returns_operation_result_on_success(self):
        """Test that successful operation result is returned."""
        result = safe_operation(lambda: 42, "Test operation")
        assert result == 42

    def test_returns_default_on_error(self):
        """Test that default is returned on error."""
        result = safe_operation(
            lambda: 1 / 0,
            "Division operation",
            default="error"
        )
        assert result == "error"

    def test_returns_none_by_default_on_error(self):
        """Test that None is returned by default on error."""
        result = safe_operation(lambda: 1 / 0, "Division operation")
        assert result is None

    def test_logs_exception_on_error(self):
        """Test that exception is logged on error."""
        with patch("utils.error_handling.log_exception") as mock_log:
            safe_operation(lambda: 1 / 0, "Division operation")
            mock_log.assert_called_once()

    def test_reraises_exception_when_requested(self):
        """Test that exception is reraised when reraise=True."""
        with pytest.raises(ZeroDivisionError):
            safe_operation(
                lambda: 1 / 0,
                "Division operation",
                reraise=True
            )

    def test_logs_before_reraising(self):
        """Test that exception is logged before reraising."""
        with patch("utils.error_handling.log_exception") as mock_log:
            with pytest.raises(ZeroDivisionError):
                safe_operation(
                    lambda: 1 / 0,
                    "Division operation",
                    reraise=True
                )
            mock_log.assert_called_once()


class TestErrorCollector:
    """Tests for ErrorCollector class."""

    def test_init_creates_empty_collector(self):
        """Test initialization creates empty collector."""
        collector = ErrorCollector("test operation")
        assert collector.operation_name == "test operation"
        assert collector.errors == []
        assert not collector.has_errors

    def test_catch_context_manager_on_success(self):
        """Test catch context manager with successful operation."""
        collector = ErrorCollector("test")

        with collector.catch("operation 1"):
            x = 1 + 1

        assert not collector.has_errors

    def test_catch_collects_errors(self):
        """Test that catch context manager collects errors."""
        collector = ErrorCollector("test")

        with collector.catch("operation 1"):
            raise ValueError("Error 1")

        assert collector.has_errors
        assert len(collector.errors) == 1
        assert "Error 1" in collector.errors[0]

    def test_catch_includes_context_in_error(self):
        """Test that context is included in error message."""
        collector = ErrorCollector("test")

        with collector.catch("processing file.xlsx"):
            raise ValueError("Invalid format")

        assert "processing file.xlsx" in collector.errors[0]

    def test_catch_continues_after_error(self):
        """Test that execution continues after error."""
        collector = ErrorCollector("test")
        results = []

        for i in range(3):
            with collector.catch(f"operation {i}"):
                if i == 1:
                    raise ValueError(f"Error at {i}")
                results.append(i)

        assert results == [0, 2]
        assert len(collector.errors) == 1

    def test_multiple_errors_collected(self):
        """Test that multiple errors are collected."""
        collector = ErrorCollector("batch import")

        with collector.catch("file 1"):
            raise ValueError("Error 1")

        with collector.catch("file 2"):
            raise KeyError("Error 2")

        with collector.catch("file 3"):
            pass  # Success

        assert len(collector.errors) == 2
        assert collector.has_errors

    def test_add_error_manually(self):
        """Test manually adding an error."""
        collector = ErrorCollector("test")
        collector.add_error("Manual error message")

        assert collector.has_errors
        assert "Manual error message" in collector.errors

    def test_get_summary_no_errors(self):
        """Test summary when no errors occurred."""
        collector = ErrorCollector("file import")
        summary = collector.get_summary()
        assert summary == "file import completed successfully"

    def test_get_summary_with_errors(self):
        """Test summary when errors occurred."""
        collector = ErrorCollector("file import")
        collector.add_error("Error 1")
        collector.add_error("Error 2")

        summary = collector.get_summary()
        assert summary == "file import completed with 2 error(s)"

    def test_logs_errors_at_warning_level(self):
        """Test that collected errors are logged at warning level."""
        collector = ErrorCollector("test")

        with patch("utils.error_handling.log_exception") as mock_log:
            with collector.catch("operation"):
                raise ValueError("Test error")

            call_args = mock_log.call_args
            assert call_args[1]["level"] == logging.WARNING

    def test_has_errors_property(self):
        """Test has_errors property."""
        collector = ErrorCollector("test")
        assert not collector.has_errors

        collector.add_error("Error")
        assert collector.has_errors
