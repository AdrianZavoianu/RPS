"""Tests for pushover context helpers."""

from services.pushover_context import (
    build_pushover_mapping,
    extend_with_underscore_variants,
    strip_direction_suffixes,
)


def test_strip_direction_suffixes_deduplicates():
    load_cases = ["Push-Mod-X+Ecc+_UX", "Push-Mod-X+Ecc+_UY", "Push-Mod-Y+Ecc+_VX"]
    stripped = strip_direction_suffixes(load_cases)
    assert stripped == ["Push-Mod-X+Ecc+", "Push-Mod-Y+Ecc+"]


def test_extend_with_underscore_variants_adds_variations():
    mapping = {"Push-Mod-X+Ecc+": "Px1", "Push-Mod-Y+Ecc-": "Py1"}
    extended = extend_with_underscore_variants(mapping)
    assert extended["Push_Mod_X+Ecc+"] == "Px1"
    assert extended["Push_Mod_Y+Ecc-"] == "Py1"


def test_build_pushover_mapping_includes_both_formats():
    cache_keys = ["Push-Mod-X+Ecc+_UX", "Push_Mod_Y+Ecc-_UY"]
    mapping = build_pushover_mapping(cache_keys)
    # Should include hyphen version from first key
    assert mapping["Push-Mod-X+Ecc+"] == "Px1"
    # Should include underscore variant for both directions
    assert mapping["Push_Mod_X+Ecc+"] == "Px1"
    assert mapping["Push_Mod_Y+Ecc-"] == "Py1"
