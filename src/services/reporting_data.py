"""Service helpers for report data queries."""

from __future__ import annotations

from contextlib import contextmanager
from typing import Callable, Optional

from sqlalchemy.orm import Session


class ReportingDataService:
    """Provide report-focused data retrieval using short-lived sessions."""

    def __init__(self, session_factory: Callable[[], Session]):
        self._session_factory = session_factory

    @contextmanager
    def _session_scope(self):
        session = self._session_factory()
        try:
            yield session
        finally:
            session.close()

    def get_beam_rotation_data(
        self,
        project_id: int,
        result_set_id: int,
        analysis_context: str,
    ) -> Optional[dict]:
        """Fetch beam rotation data for reporting."""
        import pandas as pd
        from sqlalchemy import or_
        from database.models import BeamRotation, LoadCase, Story, Element, ResultCategory

        with self._session_scope() as session:
            base_query = (
                session.query(BeamRotation, LoadCase, Story, Element)
                .join(LoadCase, BeamRotation.load_case_id == LoadCase.id)
                .join(Story, BeamRotation.story_id == Story.id)
                .join(Element, BeamRotation.element_id == Element.id)
            )

            if analysis_context == "Pushover":
                records = (
                    base_query
                    .outerjoin(ResultCategory, BeamRotation.result_category_id == ResultCategory.id)
                    .filter(
                        Story.project_id == project_id,
                        or_(
                            ResultCategory.result_set_id == result_set_id,
                            ResultCategory.result_set_id.is_(None),
                        ),
                    )
                    .order_by(Story.sort_order, Element.name, LoadCase.name)
                    .all()
                )
            else:
                records = (
                    base_query
                    .join(ResultCategory, BeamRotation.result_category_id == ResultCategory.id)
                    .filter(
                        Story.project_id == project_id,
                        ResultCategory.result_set_id == result_set_id,
                    )
                    .order_by(Story.sort_order, Element.name, LoadCase.name)
                    .all()
                )

        if not records:
            return None

        load_cases = sorted({lc.name for _, lc, _, _ in records})
        data_dict = {}
        plot_data_max = []
        plot_data_min = []

        for rotation, load_case, story, element in records:
            step_type = getattr(rotation, "step_type", None)
            rotation_value = rotation.r3_plastic * 100.0

            if step_type == "Max":
                plot_data_max.append((story.name, story.sort_order or 0, rotation_value))
            elif step_type == "Min":
                plot_data_min.append((story.name, story.sort_order or 0, rotation_value))
            else:
                plot_data_max.append((story.name, story.sort_order or 0, rotation_value))
                plot_data_min.append((story.name, story.sort_order or 0, rotation_value))

            key = (
                story.name,
                element.name,
                rotation.generated_hinge or "",
                rotation.rel_dist or 0.0,
                step_type or "",
            )
            entry = data_dict.setdefault(
                key,
                {
                    "Story": story.name,
                    "StoryOrder": story.sort_order or 0,
                    "Frame/Wall": element.name,
                    "Hinge": rotation.hinge or "",
                },
            )
            entry[load_case.name] = rotation_value

        df = pd.DataFrame(list(data_dict.values()))
        if df.empty:
            return None

        meta_cols = ["Story", "StoryOrder", "Frame/Wall", "Hinge"]
        load_case_cols = [c for c in df.columns if c not in meta_cols]

        if not load_case_cols:
            return None

        numeric_df = df[load_case_cols].apply(pd.to_numeric, errors="coerce")
        if analysis_context != "Pushover":
            df["Avg"] = numeric_df.mean(axis=1)
        df["Max"] = numeric_df.max(axis=1)
        df["Min"] = numeric_df.min(axis=1)

        df["_abs_avg"] = numeric_df.abs().mean(axis=1)
        top_10_df = df.nlargest(10, "_abs_avg").copy()

        df = df.drop(columns=["_abs_avg"])
        top_10_df = top_10_df.drop(columns=["_abs_avg"])

        stories_df = df[["Story", "StoryOrder"]].drop_duplicates().sort_values("StoryOrder")
        story_names = list(reversed(stories_df["Story"].tolist()))

        return {
            "all_data": df,
            "top_10": top_10_df,
            "load_cases": load_case_cols,
            "stories": story_names,
            "plot_data_max": plot_data_max,
            "plot_data_min": plot_data_min,
        }

    def get_column_rotation_data(
        self,
        project_id: int,
        result_set_id: int,
        analysis_context: str,
    ) -> Optional[dict]:
        """Fetch column rotation data for reporting."""
        import pandas as pd
        from sqlalchemy import or_
        from database.models import ColumnRotation, LoadCase, Story, Element, ResultCategory

        with self._session_scope() as session:
            base_query = (
                session.query(ColumnRotation, LoadCase, Story, Element)
                .join(LoadCase, ColumnRotation.load_case_id == LoadCase.id)
                .join(Story, ColumnRotation.story_id == Story.id)
                .join(Element, ColumnRotation.element_id == Element.id)
            )

            if analysis_context == "Pushover":
                records = (
                    base_query
                    .outerjoin(ResultCategory, ColumnRotation.result_category_id == ResultCategory.id)
                    .filter(
                        Story.project_id == project_id,
                        or_(
                            ResultCategory.result_set_id == result_set_id,
                            ResultCategory.result_set_id.is_(None),
                        ),
                    )
                    .order_by(Story.sort_order, Element.name, LoadCase.name)
                    .all()
                )
            else:
                records = (
                    base_query
                    .join(ResultCategory, ColumnRotation.result_category_id == ResultCategory.id)
                    .filter(
                        Story.project_id == project_id,
                        ResultCategory.result_set_id == result_set_id,
                    )
                    .order_by(Story.sort_order, Element.name, LoadCase.name)
                    .all()
                )

        if not records:
            return None

        load_cases = sorted({lc.name for _, lc, _, _ in records})
        data_dict = {}
        plot_data_max = []
        plot_data_min = []

        for rotation, load_case, story, element in records:
            if rotation.max_rotation is not None:
                rotation_value_max = rotation.max_rotation * 100.0
                plot_data_max.append((story.name, story.sort_order or 0, rotation_value_max))
            if rotation.min_rotation is not None:
                rotation_value_min = rotation.min_rotation * 100.0
                plot_data_min.append((story.name, story.sort_order or 0, rotation_value_min))

            if (
                rotation.max_rotation is None
                and rotation.min_rotation is None
                and rotation.rotation is not None
            ):
                rotation_value = rotation.rotation * 100.0
                plot_data_max.append((story.name, story.sort_order or 0, rotation_value))
                plot_data_min.append((story.name, story.sort_order or 0, rotation_value))

            table_value = None
            if rotation.max_rotation is not None and rotation.min_rotation is not None:
                if abs(rotation.max_rotation) >= abs(rotation.min_rotation):
                    table_value = rotation.max_rotation * 100.0
                else:
                    table_value = rotation.min_rotation * 100.0
            elif rotation.max_rotation is not None:
                table_value = rotation.max_rotation * 100.0
            elif rotation.min_rotation is not None:
                table_value = rotation.min_rotation * 100.0
            elif rotation.rotation is not None:
                table_value = rotation.rotation * 100.0

            key = (story.name, element.name, rotation.direction or "R3")
            entry = data_dict.setdefault(
                key,
                {
                    "Story": story.name,
                    "StoryOrder": story.sort_order or 0,
                    "Column": element.name,
                    "Dir": rotation.direction or "R3",
                },
            )
            entry[load_case.name] = table_value

        df = pd.DataFrame(list(data_dict.values()))
        if df.empty:
            return None

        meta_cols = ["Story", "StoryOrder", "Column", "Dir"]
        load_case_cols = [c for c in df.columns if c not in meta_cols]

        if not load_case_cols:
            return None

        numeric_df = df[load_case_cols].apply(pd.to_numeric, errors="coerce")
        if analysis_context != "Pushover":
            df["Avg"] = numeric_df.mean(axis=1)
        df["Max"] = numeric_df.max(axis=1)
        df["Min"] = numeric_df.min(axis=1)

        df["_abs_avg"] = numeric_df.abs().mean(axis=1)
        top_10_df = df.nlargest(10, "_abs_avg").copy()

        df = df.drop(columns=["_abs_avg"])
        top_10_df = top_10_df.drop(columns=["_abs_avg"])

        stories_df = df[["Story", "StoryOrder"]].drop_duplicates().sort_values("StoryOrder")
        story_names = list(reversed(stories_df["Story"].tolist()))

        return {
            "all_data": df,
            "top_10": top_10_df,
            "load_cases": load_case_cols,
            "stories": story_names,
            "plot_data_max": plot_data_max,
            "plot_data_min": plot_data_min,
        }
