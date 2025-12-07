"""Tests for LRU cache implementation in providers."""

from processing.result_service.providers import LRUCache


def test_lru_cache_basic_operations():
    """Test basic get/set operations."""
    cache = LRUCache(max_size=3)

    cache.set_item("a", 1)
    cache.set_item("b", 2)
    cache.set_item("c", 3)

    assert cache.get_item("a") == 1
    assert cache.get_item("b") == 2
    assert cache.get_item("c") == 3
    assert len(cache) == 3


def test_lru_cache_evicts_oldest_when_over_capacity():
    """Test that oldest items are evicted when cache exceeds max size."""
    cache = LRUCache(max_size=2)

    cache.set_item("a", 1)
    cache.set_item("b", 2)
    # Adding third item should evict "a"
    cache.set_item("c", 3)

    assert cache.get_item("a") is None
    assert cache.get_item("b") == 2
    assert cache.get_item("c") == 3
    assert len(cache) == 2


def test_lru_cache_access_updates_recency():
    """Test that accessing an item moves it to most recently used."""
    cache = LRUCache(max_size=2)

    cache.set_item("a", 1)
    cache.set_item("b", 2)
    # Access "a" to make it most recently used
    cache.get_item("a")
    # Add new item - should evict "b" (now oldest)
    cache.set_item("c", 3)

    assert cache.get_item("a") == 1
    assert cache.get_item("b") is None
    assert cache.get_item("c") == 3


def test_lru_cache_update_existing_key():
    """Test that updating existing key doesn't increase size."""
    cache = LRUCache(max_size=2)

    cache.set_item("a", 1)
    cache.set_item("b", 2)
    cache.set_item("a", 10)  # Update existing

    assert cache.get_item("a") == 10
    assert len(cache) == 2


def test_lru_cache_get_missing_returns_none():
    """Test that getting missing key returns None."""
    cache = LRUCache(max_size=2)

    assert cache.get_item("nonexistent") is None


def test_lru_cache_clear():
    """Test that clear removes all items."""
    cache = LRUCache(max_size=3)

    cache.set_item("a", 1)
    cache.set_item("b", 2)
    cache.clear()

    assert len(cache) == 0
    assert cache.get_item("a") is None


def test_lru_cache_pop():
    """Test that pop removes specific item."""
    cache = LRUCache(max_size=3)

    cache.set_item("a", 1)
    cache.set_item("b", 2)
    cache.pop("a", None)

    assert cache.get_item("a") is None
    assert cache.get_item("b") == 2
    assert len(cache) == 1
