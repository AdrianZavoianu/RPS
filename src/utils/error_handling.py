"""Standardized error handling and performance utilities.

This module provides:
1. Consistent error handling patterns for workers and UI components
2. Performance timing decorator for profiling hot paths
3. Structured context logging for errors
4. User-friendly error message formatting

Usage in QThread workers:
    from utils.error_handling import handle_worker_error

    class MyWorker(QThread):
        error = pyqtSignal(str)

        def run(self):
            try:
                # ... do work ...
            except Exception as e:
                error_msg = handle_worker_error(e, "Import failed", self.file_path)
                self.error.emit(error_msg)

Usage in UI components:
    from utils.error_handling import format_error_message, log_exception

    try:
        # ... do work ...
    except Exception as e:
        log_exception(e, "Failed to load data")
        QMessageBox.critical(self, "Error", format_error_message(e))

Performance timing usage:
    from utils.error_handling import timed

    @timed
    def expensive_operation():
        # ... do work ...
        pass

    # Enable timing with: RPS_PERF_DEBUG=1
"""

from __future__ import annotations

import logging
import os
import time
import traceback
from functools import wraps
from typing import Any, Callable, Optional, TypeVar

logger = logging.getLogger(__name__)

# Environment variable to enable performance timing
PERF_DEBUG = os.environ.get("RPS_PERF_DEBUG", "0") == "1"

F = TypeVar("F", bound=Callable[..., Any])


def timed(func: F) -> F:
    """Decorator to log execution time of functions.

    Only active when RPS_PERF_DEBUG=1 environment variable is set.
    Logs timing at DEBUG level to avoid noise in production.

    Args:
        func: Function to wrap with timing

    Returns:
        Wrapped function that logs execution time

    Example:
        @timed
        def build_cache(result_set_id: int) -> dict:
            # ... expensive operation ...
            return cache_data

        # Enable timing:
        # RPS_PERF_DEBUG=1 python src/main.py
    """
    @wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        if not PERF_DEBUG:
            return func(*args, **kwargs)

        start = time.perf_counter()
        try:
            result = func(*args, **kwargs)
            elapsed = time.perf_counter() - start
            logger.debug(f"PERF: {func.__module__}.{func.__name__} took {elapsed:.3f}s")
            return result
        except Exception:
            elapsed = time.perf_counter() - start
            logger.debug(f"PERF: {func.__module__}.{func.__name__} failed after {elapsed:.3f}s")
            raise

    return wrapper  # type: ignore


class TimingContext:
    """Context manager for timing code blocks.

    Only active when RPS_PERF_DEBUG=1 environment variable is set.

    Example:
        with TimingContext("cache_build"):
            build_cache()
            validate_cache()
    """

    def __init__(self, name: str):
        self.name = name
        self.start: float = 0

    def __enter__(self) -> "TimingContext":
        if PERF_DEBUG:
            self.start = time.perf_counter()
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        if PERF_DEBUG:
            elapsed = time.perf_counter() - self.start
            status = "failed" if exc_val else "completed"
            logger.debug(f"PERF: {self.name} {status} in {elapsed:.3f}s")


def format_error_message(
    error: Exception,
    context: Optional[str] = None,
    include_type: bool = True,
) -> str:
    """Format an exception into a user-friendly message.

    Args:
        error: The exception that occurred
        context: Optional context describing what was being done
        include_type: Whether to include the exception type name

    Returns:
        Formatted error message suitable for display to users
    """
    error_str = str(error)

    # Handle empty error messages
    if not error_str or error_str == "None":
        error_str = type(error).__name__
        include_type = False

    # Build message
    parts = []
    if context:
        parts.append(context)

    if include_type:
        parts.append(f"{type(error).__name__}: {error_str}")
    else:
        parts.append(error_str)

    return " - ".join(parts) if len(parts) > 1 else parts[0]


def log_exception(
    error: Exception,
    context: str,
    extra: Optional[dict] = None,
    level: int = logging.ERROR,
) -> None:
    """Log an exception with structured context.

    Uses logger.exception() to include the full traceback in logs,
    but doesn't print to stdout.

    Args:
        error: The exception that occurred
        context: Description of what was being done when error occurred
        extra: Additional context to include in the log record
        level: Logging level (default ERROR)
    """
    log_extra = {"event": "error", "error_type": type(error).__name__}
    if extra:
        log_extra.update(extra)

    logger.log(level, f"{context}: {error}", extra=log_extra, exc_info=True)


def handle_worker_error(
    error: Exception,
    context: str,
    *args: Any,
) -> str:
    """Handle an error in a worker thread.

    Logs the exception with context and returns a user-friendly message.
    This is the recommended pattern for QThread workers.

    Args:
        error: The exception that occurred
        context: Description of what was being done (e.g., "Import failed")
        *args: Additional context items to include in log (e.g., file_path)

    Returns:
        Formatted error message suitable for emitting via error signal

    Example:
        try:
            # ... import logic ...
        except Exception as e:
            error_msg = handle_worker_error(e, "Import failed", self.file_path)
            self.error.emit(error_msg)
    """
    # Build extra context for logging
    extra = {}
    for i, arg in enumerate(args):
        extra[f"context_{i}"] = str(arg)

    # Log with full traceback
    log_exception(error, context, extra)

    # Return user-friendly message
    return format_error_message(error, context)


def safe_operation(
    operation: Callable[[], Any],
    context: str,
    default: Any = None,
    reraise: bool = False,
) -> Any:
    """Execute an operation with standardized error handling.

    Args:
        operation: Callable to execute
        context: Description for error messages
        default: Value to return on error (if not reraising)
        reraise: Whether to reraise the exception after logging

    Returns:
        Result of operation, or default on error

    Example:
        value = safe_operation(
            lambda: int(user_input),
            "Parsing user input",
            default=0
        )
    """
    try:
        return operation()
    except Exception as e:
        log_exception(e, context)
        if reraise:
            raise
        return default


class ErrorCollector:
    """Collects errors during batch operations without stopping.

    Useful for import operations where you want to continue processing
    even if some items fail.

    Example:
        collector = ErrorCollector("file import")
        for file in files:
            with collector.catch(f"Processing {file.name}"):
                process_file(file)

        if collector.has_errors:
            for error in collector.errors:
                logger.warning(error)
            show_warning(f"{len(collector.errors)} files had errors")
    """

    def __init__(self, operation_name: str):
        self.operation_name = operation_name
        self.errors: list[str] = []
        self._current_context: Optional[str] = None

    @property
    def has_errors(self) -> bool:
        return len(self.errors) > 0

    def catch(self, context: str):
        """Context manager that catches and collects errors.

        Args:
            context: Description of current operation
        """
        self._current_context = context
        return self

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_val is not None:
            error_msg = format_error_message(exc_val, self._current_context)
            self.errors.append(error_msg)
            log_exception(
                exc_val,
                f"{self.operation_name}: {self._current_context}",
                level=logging.WARNING,
            )
            return True  # Suppress the exception
        return False

    def add_error(self, message: str) -> None:
        """Manually add an error message."""
        self.errors.append(message)
        logger.warning(f"{self.operation_name}: {message}")

    def get_summary(self) -> str:
        """Get a summary of collected errors."""
        if not self.errors:
            return f"{self.operation_name} completed successfully"
        return f"{self.operation_name} completed with {len(self.errors)} error(s)"
