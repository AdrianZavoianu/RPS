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


class GenericResultTransformer(ResultTransformer):
    """Generic transformer that works for any result type with direction suffix."""

    def __init__(self, result_type: str):
        super().__init__(result_type)

    def filter_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        """Keep only columns ending with configured direction suffix."""
        filtered_columns = [col for col in df.columns if col.endswith(self.config.direction_suffix)]
        return df[filtered_columns].copy()  # Copy to avoid SettingWithCopyWarning


class DriftTransformer(GenericResultTransformer):
    """Transformer for drift results."""
    def __init__(self):
        super().__init__('Drifts')


class AccelerationTransformer(GenericResultTransformer):
    """Transformer for acceleration results."""
    def __init__(self):
        super().__init__('Accelerations')


class ForceTransformer(GenericResultTransformer):
    """Transformer for force results."""
    def __init__(self):
        super().__init__('Forces')


class WallShearTransformer(GenericResultTransformer):
    """Transformer for wall shear results."""
    def __init__(self, direction: str):
        result_type = f'WallShears_{direction}'
        super().__init__(result_type)


class QuadRotationTransformer(GenericResultTransformer):
    """Transformer for quad rotation results (already converted to percentage in cache)."""
    def __init__(self):
        super().__init__('QuadRotations')

    def filter_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        """Keep all columns (no direction filtering needed for rotations)."""
        return df.copy()


# Transformer registry
TRANSFORMERS = {
    'Drifts': DriftTransformer(),
    'Drifts_X': GenericResultTransformer('Drifts_X'),
    'Drifts_Y': GenericResultTransformer('Drifts_Y'),
    'Accelerations': AccelerationTransformer(),
    'Accelerations_X': GenericResultTransformer('Accelerations_X'),
    'Accelerations_Y': GenericResultTransformer('Accelerations_Y'),
    'Forces': ForceTransformer(),
    'Forces_X': GenericResultTransformer('Forces_X'),
    'Forces_Y': GenericResultTransformer('Forces_Y'),
    'Displacements': GenericResultTransformer('Displacements'),
    'Displacements_X': GenericResultTransformer('Displacements_X'),
    'Displacements_Y': GenericResultTransformer('Displacements_Y'),
    'WallShears_V2': WallShearTransformer('V2'),
    'WallShears_V3': WallShearTransformer('V3'),
    'QuadRotations': QuadRotationTransformer(),
}


def get_transformer(result_type: str) -> ResultTransformer:
    """Get transformer for a result type."""
    return TRANSFORMERS.get(result_type, TRANSFORMERS['Drifts'])
