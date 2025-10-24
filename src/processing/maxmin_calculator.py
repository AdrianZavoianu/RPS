"""Calculator for absolute Max/Min drifts from source data."""

import pandas as pd
from typing import Dict, List, Tuple


def calculate_absolute_maxmin_drifts(df: pd.DataFrame) -> Dict[str, pd.DataFrame]:
    """Calculate absolute maximum drifts from Max and Min columns.

    For each load case and direction, compares the absolute values of Max and Min
    to find which one has the larger magnitude.

    Args:
        df: DataFrame with columns like "Max_TH01_X", "Min_TH01_X", etc.

    Returns:
        Dictionary with keys 'X' and 'Y', each containing a DataFrame with columns:
        - load_case: Load case name
        - absolute_max: The larger absolute value
        - sign: 'positive' if from Max, 'negative' if from Min
        - original_max: Original Max value
        - original_min: Original Min value
    """
    results = {'X': [], 'Y': []}

    # Process each direction
    for direction in ['X', 'Y']:
        # Find Max and Min columns for this direction
        max_cols = [col for col in df.columns if f'Max_' in col and col.endswith(f'_{direction}')]
        min_cols = [col for col in df.columns if f'Min_' in col and col.endswith(f'_{direction}')]

        # Match Max and Min columns by load case
        for max_col in max_cols:
            # Extract load case name from column
            # Format: "Max_TH01_X" -> "TH01"
            load_case = max_col.replace(f'_{direction}', '').replace('Max_', '')

            # Find corresponding Min column
            min_col = f'Min_{load_case}_{direction}'

            if min_col in min_cols:
                # Calculate absolute max for each row
                max_vals = df[max_col]
                min_vals = df[min_col]

                # Compare absolute values
                abs_max = max_vals.abs()
                abs_min = min_vals.abs()

                # Determine which is larger and its sign
                absolute_max = abs_max.where(abs_max >= abs_min, abs_min)
                sign = abs_max.where(abs_max >= abs_min, abs_min).apply(
                    lambda x: 'positive' if x in max_vals.values else 'negative'
                )

                # More precise sign detection
                sign_series = []
                for idx in range(len(max_vals)):
                    if abs_max.iloc[idx] >= abs_min.iloc[idx]:
                        sign_series.append('positive')
                    else:
                        sign_series.append('negative')

                results[direction].append({
                    'load_case': load_case,
                    'absolute_max': absolute_max,
                    'sign': pd.Series(sign_series, index=df.index),
                    'original_max': max_vals,
                    'original_min': min_vals
                })

    # Convert results to DataFrames
    result_dfs = {}
    for direction in ['X', 'Y']:
        if results[direction]:
            # Combine all load cases for this direction
            combined_data = []
            for load_case_data in results[direction]:
                for idx in load_case_data['absolute_max'].index:
                    combined_data.append({
                        'load_case': load_case_data['load_case'],
                        'story_idx': idx,
                        'absolute_max': load_case_data['absolute_max'].iloc[idx],
                        'sign': load_case_data['sign'].iloc[idx],
                        'original_max': load_case_data['original_max'].iloc[idx],
                        'original_min': load_case_data['original_min'].iloc[idx],
                    })

            result_dfs[direction] = pd.DataFrame(combined_data)
        else:
            result_dfs[direction] = pd.DataFrame()

    return result_dfs


def extract_load_case_from_column(column_name: str, direction: str) -> str:
    """Extract load case name from column name.

    Examples:
        "Max_TH01_X" -> "TH01"
        "Min_MCR1_Y" -> "MCR1"

    Args:
        column_name: Full column name
        direction: 'X' or 'Y'

    Returns:
        Load case name
    """
    return column_name.replace(f'_{direction}', '').replace('Max_', '').replace('Min_', '')
