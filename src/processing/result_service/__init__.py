"""Backward compatibility - re-exports from services.result_service"""
from services.result_service import (
    ResultDataService,
    ResultDataset,
    MaxMinDataset,
    ResultDatasetMeta,
    ComparisonDataset,
    ComparisonSeries,
)
from services.result_service import providers

__all__ = [
    "ResultDataService",
    "ResultDataset",
    "MaxMinDataset",
    "ResultDatasetMeta",
    "ComparisonDataset",
    "ComparisonSeries",
    "providers",
]
