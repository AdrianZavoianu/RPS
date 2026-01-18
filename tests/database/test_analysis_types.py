"""Tests for analysis type helpers."""

from config.analysis_types import AnalysisType, normalize_analysis_type, is_pushover, is_nltha


def test_normalize_analysis_type_defaults_to_nltha():
    assert normalize_analysis_type(None) == AnalysisType.NLTHA
    assert normalize_analysis_type("") == AnalysisType.NLTHA
    assert normalize_analysis_type("nltha") == AnalysisType.NLTHA


def test_normalize_analysis_type_handles_pushover_and_mixed():
    assert normalize_analysis_type("Pushover") == AnalysisType.PUSHOVER
    assert normalize_analysis_type("pushOVER") == AnalysisType.PUSHOVER
    assert normalize_analysis_type("Mixed") == AnalysisType.MIXED


def test_helper_predicates():
    assert is_pushover("Pushover") is True
    assert is_pushover("NLTHA") is False
    assert is_nltha(None) is True
    assert is_nltha("Mixed") is False
