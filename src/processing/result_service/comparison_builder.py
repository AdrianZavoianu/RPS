"""Comparison builder for multi-result-set comparisons."""

from __future__ import annotations

from typing import Dict, List, Optional

import pandas as pd

from config.result_config import ResultTypeConfig
from database.repository import ResultSetRepository

from .models import ComparisonDataset, ComparisonSeries, ResultDatasetMeta
from config.result_config import format_result_type_with_unit


def build_global_comparison(
    result_type: str,
    direction: Optional[str],
    result_set_ids: List[int],
    metric: str,
    config: ResultTypeConfig,
    get_dataset_func,  # Callable: get_standard_dataset(result_type, direction, result_set_id)
    result_set_repo: ResultSetRepository,
) -> ComparisonDataset:
    """
    Build comparison dataset for global results across multiple result sets.

    Args:
        result_type: Result type (e.g., 'Drifts', 'Forces')
        direction: Direction (e.g., 'X', 'Y')
        result_set_ids: List of result set IDs to compare
        metric: Metric to extract ('Avg', 'Max', 'Min')
        config: Result type configuration
        get_dataset_func: Function to get single result set dataset
        result_set_repo: Repository for result set names

    Returns:
        ComparisonDataset with merged data and warnings
    """
    series_list: List[ComparisonSeries] = []
    warnings: List[str] = []
    story_values: Dict[str, Dict[str, float]] = {}  # story → {result_set_name: value}
    all_stories: List[str] = []

    # Attempt to load data for each result set
    for result_set_id in result_set_ids:
        result_set = result_set_repo.get_by_id(result_set_id)
        if not result_set:
            warnings.append(f"Result set ID {result_set_id} not found")
            continue

        result_set_name = result_set.name

        try:
            # Get dataset for this result set
            dataset = get_dataset_func(result_type, direction, result_set_id)

            if not dataset:
                series_list.append(ComparisonSeries(
                    result_set_id=result_set_id,
                    result_set_name=result_set_name,
                    values={},
                    has_data=False,
                    warning=f"No data for {result_type}" + (f"_{direction}" if direction else "")
                ))
                warnings.append(f"{result_set_name} has no data for {result_type}" + (f" {direction}" if direction else ""))
                continue

            # Check if metric exists in dataset
            if metric not in dataset.summary_columns:
                series_list.append(ComparisonSeries(
                    result_set_id=result_set_id,
                    result_set_name=result_set_name,
                    values={},
                    has_data=False,
                    warning=f"Metric '{metric}' not available"
                ))
                warnings.append(f"{result_set_name}: Metric '{metric}' not available for {result_type}")
                continue

            # Extract metric column
            values = {}
            for idx, row in dataset.data.iterrows():
                story = row['Story']
                value = row.get(metric)
                if pd.notna(value):
                    values[story] = float(value)
                    if story not in story_values:
                        story_values[story] = {}
                        if not all_stories or story != all_stories[-1]:
                            all_stories.append(story)
                    story_values[story][result_set_name] = float(value)

            series_list.append(ComparisonSeries(
                result_set_id=result_set_id,
                result_set_name=result_set_name,
                values=values,
                has_data=True,
                warning=None
            ))

        except Exception as e:
            series_list.append(ComparisonSeries(
                result_set_id=result_set_id,
                result_set_name=result_set_name,
                values={},
                has_data=False,
                warning=f"Error loading data: {str(e)}"
            ))
            warnings.append(f"{result_set_name}: Error loading data - {str(e)}")

    # Build merged DataFrame
    if not all_stories:
        # No data at all
        df = pd.DataFrame(columns=["Story"])
    else:
        rows = []
        for story in all_stories:
            row = {"Story": story}
            for series in series_list:
                col_name = f"{series.result_set_name}_{metric}"
                if series.has_data and story in series.values:
                    row[col_name] = series.values[story]
                else:
                    row[col_name] = None  # Will display as "—"
            rows.append(row)

        df = pd.DataFrame(rows)

        # Add ratio column if we have at least 2 result sets with data
        series_with_data = [s for s in series_list if s.has_data]
        if len(series_with_data) >= 2:
            # Use last vs first for ratio
            first_series = series_with_data[0]
            last_series = series_with_data[-1]
            first_col = f"{first_series.result_set_name}_{metric}"
            last_col = f"{last_series.result_set_name}_{metric}"
            ratio_col = f"{last_series.result_set_name}/{first_series.result_set_name}"

            # Calculate ratio (last/first)
            df[ratio_col] = df[last_col] / df[first_col]

    # Create metadata with formatted display name including units
    meta = ResultDatasetMeta(
        result_type=result_type,
        direction=direction,
        result_set_id=result_set_ids[0] if result_set_ids else 0,  # Use first for meta
        display_name=f"Comparison: {format_result_type_with_unit(result_type, direction)}"
    )

    return ComparisonDataset(
        result_type=result_type,
        direction=direction,
        metric=metric,
        config=config,
        series=series_list,
        data=df,
        meta=meta,
        warnings=warnings
    )


def build_element_comparison(
    result_type: str,
    direction: Optional[str],
    element_id: int,
    result_set_ids: List[int],
    metric: str,
    config: ResultTypeConfig,
    get_dataset_func,  # Callable: get_element_dataset(result_type, direction, element_id, result_set_id)
    result_set_repo: ResultSetRepository,
) -> ComparisonDataset:
    """
    Build comparison dataset for element results across multiple result sets.

    Args:
        result_type: Result type (e.g., 'WallShears', 'QuadRotations')
        direction: Direction (e.g., 'V2', 'V3')
        element_id: Element ID to compare
        result_set_ids: List of result set IDs to compare
        metric: Metric to extract ('Avg', 'Max', 'Min')
        config: Result type configuration
        get_dataset_func: Function to get single result set element dataset
        result_set_repo: Repository for result set names

    Returns:
        ComparisonDataset with merged data and warnings
    """
    series_list: List[ComparisonSeries] = []
    warnings: List[str] = []
    story_values: Dict[str, Dict[str, float]] = {}
    all_stories: List[str] = []

    # Attempt to load data for each result set
    for result_set_id in result_set_ids:
        result_set = result_set_repo.get_by_id(result_set_id)
        if not result_set:
            warnings.append(f"Result set ID {result_set_id} not found")
            continue

        result_set_name = result_set.name

        try:
            # Get element dataset for this result set
            # Note: get_element_dataset signature is (element_id, result_type, direction, result_set_id)
            dataset = get_dataset_func(element_id, result_type, direction, result_set_id)

            if not dataset:
                series_list.append(ComparisonSeries(
                    result_set_id=result_set_id,
                    result_set_name=result_set_name,
                    values={},
                    has_data=False,
                    warning=f"No data for element"
                ))
                warnings.append(f"{result_set_name} has no data for this element")
                continue

            # Check if metric exists
            if metric not in dataset.summary_columns:
                series_list.append(ComparisonSeries(
                    result_set_id=result_set_id,
                    result_set_name=result_set_name,
                    values={},
                    has_data=False,
                    warning=f"Metric '{metric}' not available"
                ))
                warnings.append(f"{result_set_name}: Metric '{metric}' not available")
                continue

            # Extract metric column
            values = {}
            for idx, row in dataset.data.iterrows():
                story = row['Story']
                value = row.get(metric)
                if pd.notna(value):
                    values[story] = float(value)
                    if story not in story_values:
                        story_values[story] = {}
                        if not all_stories or story != all_stories[-1]:
                            all_stories.append(story)
                    story_values[story][result_set_name] = float(value)

            series_list.append(ComparisonSeries(
                result_set_id=result_set_id,
                result_set_name=result_set_name,
                values=values,
                has_data=True,
                warning=None
            ))

        except Exception as e:
            series_list.append(ComparisonSeries(
                result_set_id=result_set_id,
                result_set_name=result_set_name,
                values={},
                has_data=False,
                warning=f"Error loading data: {str(e)}"
            ))
            warnings.append(f"{result_set_name}: Error loading data - {str(e)}")

    # Build merged DataFrame (same logic as global)
    if not all_stories:
        df = pd.DataFrame(columns=["Story"])
    else:
        rows = []
        for story in all_stories:
            row = {"Story": story}
            for series in series_list:
                col_name = f"{series.result_set_name}_{metric}"
                if series.has_data and story in series.values:
                    row[col_name] = series.values[story]
                else:
                    row[col_name] = None
            rows.append(row)

        df = pd.DataFrame(rows)

        # Add ratio column if we have at least 2 result sets with data
        series_with_data = [s for s in series_list if s.has_data]
        if len(series_with_data) >= 2:
            # Use last vs first for ratio
            first_series = series_with_data[0]
            last_series = series_with_data[-1]
            first_col = f"{first_series.result_set_name}_{metric}"
            last_col = f"{last_series.result_set_name}_{metric}"
            ratio_col = f"{last_series.result_set_name}/{first_series.result_set_name}"

            # Calculate ratio (last/first)
            df[ratio_col] = df[last_col] / df[first_col]

    # Create metadata with formatted display name including units
    meta = ResultDatasetMeta(
        result_type=result_type,
        direction=direction,
        result_set_id=result_set_ids[0] if result_set_ids else 0,
        display_name=f"Comparison: {format_result_type_with_unit(result_type, direction)} (Element {element_id})"
    )

    return ComparisonDataset(
        result_type=result_type,
        direction=direction,
        metric=metric,
        config=config,
        series=series_list,
        data=df,
        meta=meta,
        warnings=warnings
    )


def build_joint_comparison(
    result_type: str,
    unique_name: str,
    result_set_ids: List[int],
    config: ResultTypeConfig,
    get_dataset_func,  # Callable: get_joint_dataset(result_type, result_set_id)
    result_set_repo: ResultSetRepository,
) -> ComparisonDataset:
    """
    Build comparison dataset for joint results (soil pressures, vertical displacements) across multiple result sets.

    Args:
        result_type: Result type (e.g., 'SoilPressures_Min', 'VerticalDisplacements_Min')
        unique_name: Unique name of the joint/element to compare
        result_set_ids: List of result set IDs to compare
        config: Result type configuration
        get_dataset_func: Function to get single result set joint dataset
        result_set_repo: Repository for result set names

    Returns:
        ComparisonDataset with merged data and warnings
    """
    series_list: List[ComparisonSeries] = []
    warnings: List[str] = []
    load_case_values: Dict[str, Dict[str, float]] = {}  # load_case → {result_set_name: value}
    all_load_cases: List[str] = []

    # Attempt to load data for each result set
    for result_set_id in result_set_ids:
        result_set = result_set_repo.get_by_id(result_set_id)
        if not result_set:
            warnings.append(f"Result set ID {result_set_id} not found")
            continue

        result_set_name = result_set.name

        try:
            # Get joint dataset for this result set
            dataset = get_dataset_func(result_type, result_set_id)

            if not dataset or dataset.data.empty:
                series_list.append(ComparisonSeries(
                    result_set_id=result_set_id,
                    result_set_name=result_set_name,
                    values={},
                    has_data=False,
                    warning=f"No data for {result_type}"
                ))
                warnings.append(f"{result_set_name} has no data for {result_type}")
                continue

            # Find the row with matching unique name
            matching_rows = dataset.data[dataset.data['Unique Name'] == unique_name]

            if matching_rows.empty:
                series_list.append(ComparisonSeries(
                    result_set_id=result_set_id,
                    result_set_name=result_set_name,
                    values={},
                    has_data=False,
                    warning=f"No data for {unique_name}"
                ))
                warnings.append(f"{result_set_name} has no data for {unique_name}")
                continue

            row = matching_rows.iloc[0]

            # Extract load case values (skip fixed columns and summary columns)
            values = {}
            for load_case in dataset.load_case_columns:
                value = row.get(load_case)
                if pd.notna(value):
                    values[load_case] = float(value)
                    if load_case not in load_case_values:
                        load_case_values[load_case] = {}
                        if load_case not in all_load_cases:
                            all_load_cases.append(load_case)
                    load_case_values[load_case][result_set_name] = float(value)

            series_list.append(ComparisonSeries(
                result_set_id=result_set_id,
                result_set_name=result_set_name,
                values=values,
                has_data=True,
                warning=None
            ))

        except Exception as e:
            series_list.append(ComparisonSeries(
                result_set_id=result_set_id,
                result_set_name=result_set_name,
                values={},
                has_data=False,
                warning=f"Error loading data: {str(e)}"
            ))
            warnings.append(f"{result_set_name}: Error loading data - {str(e)}")

    # Build merged DataFrame
    if not all_load_cases:
        # No data at all
        df = pd.DataFrame(columns=["Load Case"])
    else:
        rows = []
        for load_case in all_load_cases:
            row = {"Load Case": load_case}
            for series in series_list:
                col_name = f"{series.result_set_name}_Avg"
                if series.has_data and load_case in series.values:
                    row[col_name] = series.values[load_case]
                else:
                    row[col_name] = None  # Will display as "—"
            rows.append(row)

        df = pd.DataFrame(rows)

        # Add ratio column if we have at least 2 result sets with data
        series_with_data = [s for s in series_list if s.has_data]
        if len(series_with_data) >= 2:
            # Use last vs first for ratio
            first_series = series_with_data[0]
            last_series = series_with_data[-1]
            first_col = f"{first_series.result_set_name}_Avg"
            last_col = f"{last_series.result_set_name}_Avg"
            ratio_col = f"{last_series.result_set_name}/{first_series.result_set_name}"

            # Calculate ratio (last/first)
            df[ratio_col] = df[last_col] / df[first_col]

    # Create metadata with formatted display name including units
    meta = ResultDatasetMeta(
        result_type=result_type,
        direction="",
        result_set_id=result_set_ids[0] if result_set_ids else 0,
        display_name=f"Comparison: {format_result_type_with_unit(result_type, '')} - {unique_name}"
    )

    return ComparisonDataset(
        result_type=result_type,
        direction="",  # No direction for joint results
        metric="Avg",  # Joint results don't have Avg/Max/Min metrics like story results
        config=config,
        series=series_list,
        data=df,
        meta=meta,
        warnings=warnings
    )


def build_all_joints_comparison(
    result_type: str,
    result_set_ids: List[int],
    config: ResultTypeConfig,
    get_dataset_func,  # Callable: get_joint_dataset(result_type, result_set_id)
    result_set_repo: ResultSetRepository,
) -> List[tuple]:
    """
    Build comparison datasets for all joints scatter plot across multiple result sets.

    Returns data in format suitable for comparison scatter plot widget.

    Args:
        result_type: Result type (e.g., 'SoilPressures_Min', 'VerticalDisplacements_Min')
        result_set_ids: List of result set IDs to compare
        config: Result type configuration
        get_dataset_func: Function to get single result set joint dataset
        result_set_repo: Repository for result set names

    Returns:
        List of tuples (result_set_name, df_data, load_cases) where df_data contains all joints
    """
    datasets = []

    # Load data for each result set
    for result_set_id in result_set_ids:
        result_set = result_set_repo.get_by_id(result_set_id)
        if not result_set:
            continue

        result_set_name = result_set.name

        try:
            # Get joint dataset for this result set
            dataset = get_dataset_func(result_type, result_set_id)

            if not dataset or dataset.data.empty:
                continue

            # Get the full dataframe (all joints) and load case columns
            df_data = dataset.data
            load_cases = dataset.load_case_columns

            datasets.append((result_set_name, df_data, load_cases))

        except Exception:
            continue

    return datasets
