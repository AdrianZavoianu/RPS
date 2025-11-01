"""Result data service facade and supporting components."""

from .models import ResultDataset, MaxMinDataset, ResultDatasetMeta
from .service import ResultDataService

__all__ = [
    "ResultDataService",
    "ResultDataset",
    "MaxMinDataset",
    "ResultDatasetMeta",
]
