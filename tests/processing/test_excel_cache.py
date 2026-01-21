"""Tests for Excel file cache functionality."""

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from processing.excel_cache import ExcelFileCache, read_excel_cached, get_sheet_names_cached


@pytest.fixture
def temp_excel_file():
    """Create a temporary Excel file for testing."""
    with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as f:
        path = Path(f.name)

    # Create a simple Excel file with test data
    df = pd.DataFrame({"A": [1, 2, 3], "B": [4, 5, 6]})
    with pd.ExcelWriter(path, engine="openpyxl") as writer:
        df.to_excel(writer, sheet_name="Sheet1", index=False)
        df.to_excel(writer, sheet_name="Sheet2", index=False)

    yield path

    # Cleanup
    ExcelFileCache.clear_all()
    try:
        path.unlink()
    except Exception:
        pass


@pytest.fixture(autouse=True)
def clear_cache():
    """Clear cache before each test."""
    ExcelFileCache.clear_all()
    yield
    ExcelFileCache.clear_all()


class TestExcelFileCache:
    """Tests for ExcelFileCache class."""

    def test_acquire_and_release(self, temp_excel_file):
        """Test basic acquire and release functionality."""
        # Acquire file
        xl = ExcelFileCache.acquire(temp_excel_file)
        assert xl is not None
        assert ExcelFileCache.is_cached(temp_excel_file)
        assert ExcelFileCache.get_ref_count(temp_excel_file) == 1

        # Release file
        ExcelFileCache.release(temp_excel_file)
        assert not ExcelFileCache.is_cached(temp_excel_file)
        assert ExcelFileCache.get_ref_count(temp_excel_file) == 0

    def test_multiple_acquires(self, temp_excel_file):
        """Test multiple acquires increment reference count."""
        xl1 = ExcelFileCache.acquire(temp_excel_file)
        xl2 = ExcelFileCache.acquire(temp_excel_file)

        # Should be the same object
        assert xl1 is xl2
        assert ExcelFileCache.get_ref_count(temp_excel_file) == 2

        # Release one
        ExcelFileCache.release(temp_excel_file)
        assert ExcelFileCache.is_cached(temp_excel_file)
        assert ExcelFileCache.get_ref_count(temp_excel_file) == 1

        # Release second
        ExcelFileCache.release(temp_excel_file)
        assert not ExcelFileCache.is_cached(temp_excel_file)

    def test_context_manager(self, temp_excel_file):
        """Test context manager acquire/release."""
        with ExcelFileCache.get_file(temp_excel_file) as xl:
            assert xl is not None
            assert ExcelFileCache.is_cached(temp_excel_file)

        # Should be released after context exits
        assert not ExcelFileCache.is_cached(temp_excel_file)

    def test_context_manager_with_exception(self, temp_excel_file):
        """Test context manager releases on exception."""
        with pytest.raises(ValueError):
            with ExcelFileCache.get_file(temp_excel_file) as xl:
                assert ExcelFileCache.is_cached(temp_excel_file)
                raise ValueError("Test error")

        # Should still be released after exception
        assert not ExcelFileCache.is_cached(temp_excel_file)

    def test_clear_specific_file(self, temp_excel_file):
        """Test clearing a specific file from cache."""
        ExcelFileCache.acquire(temp_excel_file)
        ExcelFileCache.acquire(temp_excel_file)
        assert ExcelFileCache.get_ref_count(temp_excel_file) == 2

        # Force clear
        ExcelFileCache.clear(temp_excel_file)
        assert not ExcelFileCache.is_cached(temp_excel_file)

    def test_clear_all(self, temp_excel_file):
        """Test clearing all files from cache."""
        # Create second temp file
        with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as f:
            path2 = Path(f.name)
        df = pd.DataFrame({"X": [1]})
        df.to_excel(path2, index=False)

        try:
            ExcelFileCache.acquire(temp_excel_file)
            ExcelFileCache.acquire(path2)

            stats = ExcelFileCache.stats()
            assert stats["files_cached"] == 2

            ExcelFileCache.clear_all()

            stats = ExcelFileCache.stats()
            assert stats["files_cached"] == 0
            assert stats["total_refs"] == 0
        finally:
            try:
                path2.unlink()
            except Exception:
                pass

    def test_stats(self, temp_excel_file):
        """Test cache statistics."""
        stats = ExcelFileCache.stats()
        assert stats["files_cached"] == 0
        assert stats["total_refs"] == 0

        ExcelFileCache.acquire(temp_excel_file)
        ExcelFileCache.acquire(temp_excel_file)

        stats = ExcelFileCache.stats()
        assert stats["files_cached"] == 1
        assert stats["total_refs"] == 2

    def test_release_uncached_file(self, temp_excel_file):
        """Test releasing a file that's not in cache (should not error)."""
        # Should not raise an error
        ExcelFileCache.release(temp_excel_file)

    def test_path_normalization(self, temp_excel_file):
        """Test that different path representations resolve to same cache entry."""
        # Use string path
        xl1 = ExcelFileCache.acquire(str(temp_excel_file))

        # Use Path object
        xl2 = ExcelFileCache.acquire(temp_excel_file)

        # Should be the same cached object
        assert xl1 is xl2
        assert ExcelFileCache.get_ref_count(temp_excel_file) == 2

        ExcelFileCache.clear_all()


class TestCacheConvenienceFunctions:
    """Tests for convenience functions."""

    def test_read_excel_cached(self, temp_excel_file):
        """Test read_excel_cached function."""
        df = read_excel_cached(temp_excel_file, "Sheet1")

        assert isinstance(df, pd.DataFrame)
        assert list(df.columns) == ["A", "B"]
        assert len(df) == 3

        # Cache should be released after function returns
        assert not ExcelFileCache.is_cached(temp_excel_file)

    def test_get_sheet_names_cached(self, temp_excel_file):
        """Test get_sheet_names_cached function."""
        names = get_sheet_names_cached(temp_excel_file)

        assert names == ["Sheet1", "Sheet2"]

        # Cache should be released after function returns
        assert not ExcelFileCache.is_cached(temp_excel_file)

    def test_read_excel_cached_with_kwargs(self, temp_excel_file):
        """Test read_excel_cached with additional pandas arguments."""
        df = read_excel_cached(temp_excel_file, "Sheet1", nrows=2)

        assert len(df) == 2
