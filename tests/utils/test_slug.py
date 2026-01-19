"""Tests for slug generation utilities."""

import pytest

from utils.slug import slugify, SLUG_INVALID


class TestSlugify:
    """Tests for slugify function."""

    def test_converts_to_lowercase(self):
        """Should convert text to lowercase."""
        assert slugify("HELLO") == "hello"
        assert slugify("Hello World") == "hello-world"

    def test_replaces_spaces_with_hyphens(self):
        """Should replace spaces with hyphens."""
        assert slugify("hello world") == "hello-world"
        assert slugify("foo   bar") == "foo-bar"

    def test_replaces_special_chars_with_hyphens(self):
        """Should replace special characters with hyphens."""
        assert slugify("hello@world") == "hello-world"
        assert slugify("foo_bar") == "foo-bar"
        assert slugify("test!@#$%test") == "test-test"

    def test_removes_leading_trailing_hyphens(self):
        """Should strip leading and trailing hyphens."""
        assert slugify("  hello  ") == "hello"
        assert slugify("--test--") == "test"

    def test_handles_numbers(self):
        """Should preserve numbers."""
        assert slugify("test123") == "test123"
        assert slugify("Project 2024") == "project-2024"

    def test_collapses_multiple_hyphens(self):
        """Should collapse multiple hyphens into one."""
        assert slugify("foo---bar") == "foo-bar"
        assert slugify("a   b   c") == "a-b-c"

    def test_raises_for_empty_string_no_default(self):
        """Should raise ValueError for empty string without default."""
        with pytest.raises(ValueError, match="Cannot slugify empty text"):
            slugify("")

        with pytest.raises(ValueError, match="Cannot slugify empty text"):
            slugify("   ")

    def test_uses_default_for_empty_string(self):
        """Should use default when text is empty."""
        assert slugify("", default="untitled") == "untitled"
        assert slugify("   ", default="My Default") == "my-default"

    def test_none_uses_default(self):
        """Should use default when text is None."""
        assert slugify(None, default="fallback") == "fallback"

    def test_returns_project_as_ultimate_fallback(self):
        """Should return 'project' when all else fails."""
        # Edge case: empty after processing but default provided
        assert slugify("@#$%", default="project") == "project"


class TestSlugInvalidRegex:
    """Tests for the SLUG_INVALID regex pattern."""

    def test_matches_special_characters(self):
        """Should match special characters."""
        assert SLUG_INVALID.search("@") is not None
        assert SLUG_INVALID.search("!") is not None
        assert SLUG_INVALID.search("#") is not None

    def test_matches_spaces(self):
        """Should match whitespace."""
        assert SLUG_INVALID.search(" ") is not None
        assert SLUG_INVALID.search("\t") is not None

    def test_does_not_match_lowercase_alphanumeric(self):
        """Should not match lowercase letters and digits."""
        assert SLUG_INVALID.search("abc") is None
        assert SLUG_INVALID.search("123") is None
        assert SLUG_INVALID.search("abc123") is None

    def test_matches_uppercase(self):
        """Should match uppercase letters (not in [a-z0-9])."""
        assert SLUG_INVALID.search("A") is not None
        assert SLUG_INVALID.search("ABC") is not None
