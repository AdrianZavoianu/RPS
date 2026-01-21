"""Centralized Excel file caching for improved IO performance.

This module provides a thread-safe cache for pd.ExcelFile objects,
reducing repeated disk reads when multiple parsers/importers need
to access the same Excel file.

Usage:
    # Simple context manager (auto-cleanup)
    with ExcelFileCache.get_file(path) as xl:
        df = pd.read_excel(xl, sheet_name="Sheet1")

    # Manual management (for batch operations)
    xl = ExcelFileCache.acquire(path)
    try:
        # ... multiple operations ...
    finally:
        ExcelFileCache.release(path)

    # Clear all cached files (e.g., after import batch)
    ExcelFileCache.clear_all()
"""

from __future__ import annotations

import logging
import threading
from contextlib import contextmanager
from pathlib import Path
from typing import Dict, Iterator, Optional, Union

import pandas as pd

logger = logging.getLogger(__name__)


class ExcelFileCache:
    """Thread-safe cache for pd.ExcelFile objects.

    This cache uses reference counting to track usage and automatically
    closes files when they're no longer needed. Files are identified by
    their absolute path.

    Thread Safety:
        All operations are protected by a lock, making this safe for use
        across multiple threads (e.g., in QThread workers).
    """

    _cache: Dict[str, pd.ExcelFile] = {}
    _ref_counts: Dict[str, int] = {}
    _lock = threading.Lock()

    @classmethod
    def _normalize_path(cls, path: Union[Path, str]) -> str:
        """Normalize path to absolute string for consistent cache keys."""
        if isinstance(path, str):
            path = Path(path)
        return str(path.resolve())

    @classmethod
    def acquire(cls, path: Union[Path, str]) -> pd.ExcelFile:
        """Acquire an ExcelFile handle from the cache.

        If the file is not cached, it will be opened and cached.
        Reference count is incremented for each acquire.

        Args:
            path: Path to the Excel file.

        Returns:
            pd.ExcelFile handle for the requested file.

        Raises:
            FileNotFoundError: If the file doesn't exist.
            ValueError: If the file cannot be opened as Excel.
        """
        key = cls._normalize_path(path)

        with cls._lock:
            if key not in cls._cache:
                logger.debug(f"Opening Excel file: {key}")
                cls._cache[key] = pd.ExcelFile(path)
                cls._ref_counts[key] = 0

            cls._ref_counts[key] += 1
            logger.debug(f"Acquired Excel file (refs={cls._ref_counts[key]}): {key}")
            return cls._cache[key]

    @classmethod
    def release(cls, path: Union[Path, str]) -> None:
        """Release an ExcelFile handle back to the cache.

        Decrements reference count. When count reaches zero, the file
        is closed and removed from cache.

        Args:
            path: Path to the Excel file to release.
        """
        key = cls._normalize_path(path)

        with cls._lock:
            if key not in cls._cache:
                logger.warning(f"Attempted to release uncached file: {key}")
                return

            cls._ref_counts[key] -= 1
            logger.debug(f"Released Excel file (refs={cls._ref_counts[key]}): {key}")

            if cls._ref_counts[key] <= 0:
                logger.debug(f"Closing Excel file (no refs): {key}")
                try:
                    cls._cache[key].close()
                except Exception as e:
                    logger.warning(f"Error closing Excel file {key}: {e}")
                del cls._cache[key]
                del cls._ref_counts[key]

    @classmethod
    @contextmanager
    def get_file(cls, path: Union[Path, str]) -> Iterator[pd.ExcelFile]:
        """Context manager for acquiring and releasing an Excel file.

        Usage:
            with ExcelFileCache.get_file("data.xlsx") as xl:
                df = pd.read_excel(xl, sheet_name="Sheet1")

        Args:
            path: Path to the Excel file.

        Yields:
            pd.ExcelFile handle.
        """
        xl = cls.acquire(path)
        try:
            yield xl
        finally:
            cls.release(path)

    @classmethod
    def is_cached(cls, path: Union[Path, str]) -> bool:
        """Check if a file is currently in the cache."""
        key = cls._normalize_path(path)
        with cls._lock:
            return key in cls._cache

    @classmethod
    def get_ref_count(cls, path: Union[Path, str]) -> int:
        """Get the current reference count for a cached file."""
        key = cls._normalize_path(path)
        with cls._lock:
            return cls._ref_counts.get(key, 0)

    @classmethod
    def clear(cls, path: Union[Path, str]) -> None:
        """Force-clear a specific file from the cache.

        This will close the file regardless of reference count.
        Use with caution - may affect other users of the file.

        Args:
            path: Path to the Excel file to clear.
        """
        key = cls._normalize_path(path)

        with cls._lock:
            if key in cls._cache:
                logger.debug(f"Force-clearing Excel file from cache: {key}")
                try:
                    cls._cache[key].close()
                except Exception as e:
                    logger.warning(f"Error closing Excel file {key}: {e}")
                del cls._cache[key]
                del cls._ref_counts[key]

    @classmethod
    def clear_all(cls) -> None:
        """Clear all files from the cache.

        This should be called after batch import operations to free
        memory and file handles.
        """
        with cls._lock:
            for key, xl in list(cls._cache.items()):
                logger.debug(f"Clearing Excel file from cache: {key}")
                try:
                    xl.close()
                except Exception as e:
                    logger.warning(f"Error closing Excel file {key}: {e}")

            cls._cache.clear()
            cls._ref_counts.clear()
            logger.debug("Excel file cache cleared")

    @classmethod
    def stats(cls) -> Dict[str, int]:
        """Get cache statistics.

        Returns:
            Dict with 'files_cached' and 'total_refs' counts.
        """
        with cls._lock:
            return {
                "files_cached": len(cls._cache),
                "total_refs": sum(cls._ref_counts.values()),
            }


def read_excel_cached(
    path: Union[Path, str],
    sheet_name: str,
    **kwargs
) -> pd.DataFrame:
    """Read an Excel sheet using the cache.

    Convenience function that handles acquire/release automatically.

    Args:
        path: Path to the Excel file.
        sheet_name: Name of the sheet to read.
        **kwargs: Additional arguments passed to pd.read_excel.

    Returns:
        DataFrame with the sheet contents.
    """
    with ExcelFileCache.get_file(path) as xl:
        return pd.read_excel(xl, sheet_name=sheet_name, **kwargs)


def get_sheet_names_cached(path: Union[Path, str]) -> list:
    """Get sheet names from an Excel file using the cache.

    Args:
        path: Path to the Excel file.

    Returns:
        List of sheet names in the file.
    """
    with ExcelFileCache.get_file(path) as xl:
        return xl.sheet_names
