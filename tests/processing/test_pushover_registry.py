"""Tests for the pushover importer/parser registry."""

import pytest

from processing.pushover.pushover_registry import (
    PushoverRegistry,
    get_pushover_importer,
    get_pushover_parser,
)


class TestPushoverRegistryTypes:
    """Test type categorization."""

    def test_all_types_is_union_of_categories(self):
        """ALL_TYPES should be the union of all category sets."""
        expected = (
            PushoverRegistry.GLOBAL_TYPES
            | PushoverRegistry.ELEMENT_TYPES
            | PushoverRegistry.JOINT_TYPES
            | PushoverRegistry.CURVE_TYPES
        )
        assert PushoverRegistry.ALL_TYPES == expected

    def test_global_types_contains_global(self):
        assert "global" in PushoverRegistry.GLOBAL_TYPES

    def test_element_types_contains_expected(self):
        expected = {"wall", "beam", "column", "column_shear"}
        assert PushoverRegistry.ELEMENT_TYPES == expected

    def test_joint_types_contains_expected(self):
        expected = {"soil_pressure", "vert_displacement", "joint"}
        assert PushoverRegistry.JOINT_TYPES == expected

    def test_curve_types_contains_curve(self):
        assert "curve" in PushoverRegistry.CURVE_TYPES


class TestGetImporter:
    """Test importer class retrieval."""

    def setup_method(self):
        """Clear cache before each test."""
        PushoverRegistry.clear_cache()

    def test_get_importer_returns_class_for_valid_type(self):
        """Should return importer class for valid result type."""
        importer_class = PushoverRegistry.get_importer("curve")
        assert importer_class is not None
        assert importer_class.__name__ == "PushoverImporter"

    def test_get_importer_case_insensitive(self):
        """Should handle case-insensitive lookups."""
        lower = PushoverRegistry.get_importer("curve")
        upper = PushoverRegistry.get_importer("CURVE")
        mixed = PushoverRegistry.get_importer("Curve")
        assert lower == upper == mixed

    def test_get_importer_returns_none_for_unknown_type(self):
        """Should return None for unknown result types."""
        result = PushoverRegistry.get_importer("unknown_type")
        assert result is None

    def test_get_importer_caches_result(self):
        """Should cache loaded classes."""
        first = PushoverRegistry.get_importer("curve")
        second = PushoverRegistry.get_importer("curve")
        assert first is second
        assert "curve" in PushoverRegistry._importer_cache

    @pytest.mark.parametrize("result_type", [
        "global", "wall", "beam", "column", "column_shear",
        "soil_pressure", "vert_displacement", "joint", "curve"
    ])
    def test_get_importer_all_types_loadable(self, result_type):
        """All registered types should be loadable."""
        importer_class = PushoverRegistry.get_importer(result_type)
        assert importer_class is not None


class TestGetParser:
    """Test parser class retrieval."""

    def setup_method(self):
        """Clear cache before each test."""
        PushoverRegistry.clear_cache()

    def test_get_parser_returns_class_for_valid_type(self):
        """Should return parser class for valid result type."""
        parser_class = PushoverRegistry.get_parser("curve")
        assert parser_class is not None
        assert parser_class.__name__ == "PushoverParser"

    def test_get_parser_case_insensitive(self):
        """Should handle case-insensitive lookups."""
        lower = PushoverRegistry.get_parser("beam")
        upper = PushoverRegistry.get_parser("BEAM")
        assert lower == upper

    def test_get_parser_returns_none_for_unknown_type(self):
        """Should return None for unknown result types."""
        result = PushoverRegistry.get_parser("nonexistent")
        assert result is None

    def test_get_parser_caches_result(self):
        """Should cache loaded classes."""
        first = PushoverRegistry.get_parser("global")
        second = PushoverRegistry.get_parser("global")
        assert first is second
        assert "global" in PushoverRegistry._parser_cache

    @pytest.mark.parametrize("result_type", [
        "global", "wall", "beam", "column", "column_shear",
        "soil_pressure", "vert_displacement", "joint", "curve"
    ])
    def test_get_parser_all_types_loadable(self, result_type):
        """All registered types should be loadable."""
        parser_class = PushoverRegistry.get_parser(result_type)
        assert parser_class is not None


class TestHelperMethods:
    """Test helper and utility methods."""

    def test_get_available_types_returns_sorted_list(self):
        """Should return sorted list of all types."""
        types = PushoverRegistry.get_available_types()
        assert isinstance(types, list)
        assert types == sorted(types)
        assert set(types) == PushoverRegistry.ALL_TYPES

    def test_get_element_types_returns_sorted_list(self):
        """Should return sorted list of element types."""
        types = PushoverRegistry.get_element_types()
        assert isinstance(types, list)
        assert types == sorted(types)
        assert set(types) == PushoverRegistry.ELEMENT_TYPES

    def test_get_joint_types_returns_sorted_list(self):
        """Should return sorted list of joint types."""
        types = PushoverRegistry.get_joint_types()
        assert isinstance(types, list)
        assert types == sorted(types)
        assert set(types) == PushoverRegistry.JOINT_TYPES

    def test_is_element_type_true_for_elements(self):
        """Should return True for element types."""
        assert PushoverRegistry.is_element_type("wall") is True
        assert PushoverRegistry.is_element_type("beam") is True
        assert PushoverRegistry.is_element_type("column") is True

    def test_is_element_type_false_for_non_elements(self):
        """Should return False for non-element types."""
        assert PushoverRegistry.is_element_type("global") is False
        assert PushoverRegistry.is_element_type("curve") is False
        assert PushoverRegistry.is_element_type("soil_pressure") is False

    def test_is_joint_type_true_for_joints(self):
        """Should return True for joint types."""
        assert PushoverRegistry.is_joint_type("soil_pressure") is True
        assert PushoverRegistry.is_joint_type("vert_displacement") is True
        assert PushoverRegistry.is_joint_type("joint") is True

    def test_is_joint_type_false_for_non_joints(self):
        """Should return False for non-joint types."""
        assert PushoverRegistry.is_joint_type("wall") is False
        assert PushoverRegistry.is_joint_type("global") is False

    def test_clear_cache_empties_both_caches(self):
        """Clear cache should empty both importer and parser caches."""
        # Populate caches
        PushoverRegistry.get_importer("curve")
        PushoverRegistry.get_parser("curve")
        assert len(PushoverRegistry._importer_cache) > 0
        assert len(PushoverRegistry._parser_cache) > 0

        # Clear
        PushoverRegistry.clear_cache()
        assert len(PushoverRegistry._importer_cache) == 0
        assert len(PushoverRegistry._parser_cache) == 0


class TestConvenienceFunctions:
    """Test module-level convenience functions."""

    def setup_method(self):
        PushoverRegistry.clear_cache()

    def test_get_pushover_importer_delegates_to_registry(self):
        """Convenience function should delegate to registry."""
        result = get_pushover_importer("curve")
        assert result == PushoverRegistry.get_importer("curve")

    def test_get_pushover_parser_delegates_to_registry(self):
        """Convenience function should delegate to registry."""
        result = get_pushover_parser("beam")
        assert result == PushoverRegistry.get_parser("beam")
