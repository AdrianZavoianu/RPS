"""Result data service facade and supporting components."""

from .models import ResultDataset, MaxMinDataset, ResultDatasetMeta, ComparisonDataset, ComparisonSeries
from .service import ResultDataService

__all__ = [
    "ResultDataService",
    "ResultDataset",
    "MaxMinDataset",
    "ResultDatasetMeta",
    "ComparisonDataset",
    "ComparisonSeries",
]
