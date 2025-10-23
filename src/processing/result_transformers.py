"""Data transformers for different result types."""

import pandas as pd
from abc import ABC, abstractmethod
from config.result_config import get_config


class ResultTransformer(ABC):
    """Base class for result-specific data transformations."""

    def __init__(self, result_type: str):
        self.result_type = result_type
        self.config = get_config(result_type)

    @abstractmethod
    def filter_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        """Filter relevant columns for this result type."""
        pass

    def clean_column_names(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Clean and standardize column names.

        Default implementation extracts load case name from columns like:
        "160Wil_DES_Global_TH01_X" -> "TH01"
        """
        cleaned_columns = []
        for col in df.columns:
            # Remove direction suffix
            col_without_suffix = col.replace(self.config.direction_suffix, '')
            # Get the last part after splitting by underscore (load case name)
            parts = col_without_suffix.split('_')
            load_case_name = parts[-1] if parts else col_without_suffix
            cleaned_columns.append(load_case_name)

        df.columns = cleaned_columns
        return df

    def add_statistics(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Add computed statistics columns (Avg, Max, Min).

        Default implementation calculates across all numeric columns.
        """
        numeric_data = df.apply(pd.to_numeric, errors='coerce')
        df['Avg'] = numeric_data.mean(axis=1)
        df['Max'] = numeric_data.max(axis=1)
        df['Min'] = numeric_data.min(axis=1)
        return df

    def transform(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Full transformation pipeline.

        1. Filter relevant columns
        2. Clean column names
        3. Add statistics
        """
        df = self.filter_columns(df)
        df = self.clean_column_names(df)
        df = self.add_statistics(df)
        return df


class DriftTransformer(ResultTransformer):
    """Transformer for drift results (X direction)."""

    def __init__(self):
        super().__init__('Drifts')

    def filter_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        """Keep only columns ending with _X."""
        x_columns = [col for col in df.columns if col.endswith(self.config.direction_suffix)]
        return df[x_columns].copy()  # Copy to avoid SettingWithCopyWarning


class AccelerationTransformer(ResultTransformer):
    """Transformer for acceleration results (UX direction)."""

    def __init__(self):
        super().__init__('Accelerations')

    def filter_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        """Keep only columns ending with _UX."""
        ux_columns = [col for col in df.columns if col.endswith(self.config.direction_suffix)]
        return df[ux_columns].copy()  # Copy to avoid SettingWithCopyWarning


class ForceTransformer(ResultTransformer):
    """Transformer for force results (VX direction)."""

    def __init__(self):
        super().__init__('Forces')

    def filter_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        """Keep only columns ending with _VX."""
        vx_columns = [col for col in df.columns if col.endswith(self.config.direction_suffix)]
        return df[vx_columns].copy()  # Copy to avoid SettingWithCopyWarning


# Transformer registry
TRANSFORMERS = {
    'Drifts': DriftTransformer(),
    'Accelerations': AccelerationTransformer(),
    'Forces': ForceTransformer(),
}


def get_transformer(result_type: str) -> ResultTransformer:
    """Get transformer for a result type."""
    return TRANSFORMERS.get(result_type, TRANSFORMERS['Drifts'])
