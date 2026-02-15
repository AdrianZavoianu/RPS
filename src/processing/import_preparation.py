"""Headless helpers for preparing enhanced imports."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Dict, Iterable, List, Optional, Sequence, Set, Tuple

from .excel_parser import ExcelParser


@dataclass
class FilePrescanSummary:
    """Summary for a single Excel file."""

    load_cases_by_sheet: Dict[str, List[str]]
    available_sheets: Set[str]
    foundation_joints: List[str]


@dataclass
class PrescanResult:
    """Results from scanning a folder of Excel files."""

    file_load_cases: Dict[str, Dict[str, List[str]]] = field(default_factory=dict)
    file_summaries: Dict[str, FilePrescanSummary] = field(default_factory=dict)
    foundation_joints: List[str] = field(default_factory=list)
    files_scanned: int = 0
    errors: List[str] = field(default_factory=list)


class ImportPreparationService:
    """Collects metadata needed before running the enhanced import."""

    def __init__(
        self,
        target_sheets: Dict[str, List[str]],
        parser_factory: Callable[[Path], ExcelParser] = ExcelParser,
    ) -> None:
        self._target_sheets = target_sheets
        self._parser_factory = parser_factory

    def prescan_folder(
        self,
        folder_path: Path,
        result_types: Optional[Set[str]] = None,
        progress_callback: Optional[Callable[[str, int, int], None]] = None,
    ) -> PrescanResult:
        """Prescan every Excel file under a folder."""
        files: List[Path] = []
        for pattern in ("*.xlsx", "*.xls"):
            files.extend(folder_path.glob(pattern))
        excel_files = sorted(f for f in files if not f.name.startswith("~$"))
        return self.prescan_files(excel_files, result_types, progress_callback)

    def prescan_files(
        self,
        excel_files: Sequence[Path],
        result_types: Optional[Set[str]] = None,
        progress_callback: Optional[Callable[[str, int, int], None]] = None,
    ) -> PrescanResult:
        """Prescan a provided list of Excel files."""
        result = PrescanResult(files_scanned=len(excel_files))
        foundation_seen: Set[str] = set()

        def _scan_file(
            file_path: Path,
        ) -> Tuple[str, Dict[str, List[str]], List[str], List[str], List[str], Set[str]]:
            parser = self._parser_factory(file_path)
            load_cases_by_sheet: Dict[str, List[str]] = {}
            sheets_found: List[str] = []
            sheets_errored: List[str] = []
            available_sheets = set(parser.get_available_sheets())
            foundation_joints: List[str] = []

            for sheet_name, result_labels in self._target_sheets.items():
                if not self._should_import_any(result_labels, result_types):
                    continue
                if sheet_name not in available_sheets and sheet_name != "Vertical Displacements":
                    continue

                try:
                    load_cases = self._extract_load_cases_from_sheet(parser, sheet_name)
                    if load_cases:
                        load_cases_by_sheet[sheet_name] = load_cases
                        sheets_found.append(f"{sheet_name}({len(load_cases)})")
                except Exception as exc:  # noqa: PERF203
                    sheets_errored.append(f"{sheet_name}: {str(exc)[:30]}")

            if "Fou" in available_sheets:
                try:
                    foundation_joints = parser.get_foundation_joints()
                except Exception as exc:  # noqa: PERF203
                    sheets_errored.append(f"Fou: {str(exc)[:30]}")

            if "Joint Displacements" in available_sheets:
                if result_types is None or "vertical displacements" in result_types:
                    try:
                        if hasattr(parser, "get_load_cases_only"):
                            load_cases = parser.get_load_cases_only("Joint Displacements") or []
                        else:
                            _, load_cases, _ = parser.get_joint_displacements()
                        if load_cases:
                            load_cases_by_sheet["Vertical Displacements"] = load_cases
                            sheets_found.append(f"Vertical Displacements({len(load_cases)})")
                    except Exception as exc:  # noqa: PERF203
                        sheets_errored.append(f"Joint Displacements: {str(exc)[:30]}")

            return (
                file_path.name,
                load_cases_by_sheet,
                sheets_found,
                sheets_errored,
                foundation_joints,
                available_sheets,
            )

        with ThreadPoolExecutor(max_workers=min(6, len(excel_files) or 1)) as executor:
            futures = {executor.submit(_scan_file, path): (idx, path) for idx, path in enumerate(excel_files)}
            for future in as_completed(futures):
                idx, file_path = futures[future]
                if progress_callback:
                    progress_callback(f"Scanning {file_path.name}...", idx, len(excel_files))
                try:
                    (
                        file_name,
                        load_cases_by_sheet,
                        sheets_found,
                        sheets_errored,
                        joints,
                        available_sheets,
                    ) = future.result()

                    if load_cases_by_sheet:
                        result.file_load_cases[file_name] = load_cases_by_sheet

                    result.file_summaries[file_name] = FilePrescanSummary(
                        load_cases_by_sheet=load_cases_by_sheet,
                        available_sheets=available_sheets,
                        foundation_joints=joints,
                    )

                    for joint in joints:
                        if joint not in foundation_seen:
                            foundation_seen.add(joint)
                            result.foundation_joints.append(joint)

                    if progress_callback and (sheets_found or sheets_errored):
                        if sheets_found:
                            progress_callback(
                                f"  ✓ {', '.join(sheets_found[:3])}"
                                f"{'...' if len(sheets_found) > 3 else ''}",
                                idx,
                                len(excel_files),
                            )
                        if sheets_errored:
                            progress_callback(
                                f"  ✗ {sheets_errored[0]}",
                                idx,
                                len(excel_files),
                            )
                except Exception as exc:  # noqa: PERF203
                    result.errors.append(f"{file_path.name}: {exc}")

        return result

    def _should_import_any(self, labels: Iterable[str], result_types: Optional[Set[str]]) -> bool:
        if not result_types:
            return True
        for label in labels:
            if label.strip().lower() in result_types:
                return True
        return False

    def _extract_load_cases_from_sheet(self, parser: ExcelParser, sheet_name: str) -> List[str]:
        if hasattr(parser, "get_load_cases_only"):
            quick_cases = parser.get_load_cases_only(sheet_name)
            if quick_cases is not None:
                return quick_cases
        if sheet_name == "Story Drifts":
            _, load_cases, _ = parser.get_story_drifts()
            return load_cases
        if sheet_name == "Diaphragm Accelerations":
            _, load_cases, _ = parser.get_story_accelerations()
            return load_cases
        if sheet_name == "Story Forces":
            _, load_cases, _ = parser.get_story_forces()
            return load_cases
        if sheet_name == "Joint Displacements":
            _, load_cases, _ = parser.get_joint_displacements()
            return load_cases
        if sheet_name == "Pier Forces":
            _, load_cases, _, _ = parser.get_pier_forces()
            return load_cases
        if sheet_name == "Element Forces - Columns":
            _, load_cases, _, _ = parser.get_column_forces()
            return load_cases
        if sheet_name == "Fiber Hinge States":
            _, load_cases, _, _ = parser.get_fiber_hinge_states()
            return load_cases
        if sheet_name == "Hinge States":
            _, load_cases, _, _ = parser.get_hinge_states()
            return load_cases
        if sheet_name == "Quad Strain Gauge - Rotation":
            _, load_cases, _, _ = parser.get_quad_rotations()
            return load_cases
        if sheet_name == "Soil Pressures":
            _, load_cases, _ = parser.get_soil_pressures()
            return load_cases
        return []


def detect_conflicts(
    file_load_cases: Dict[str, Dict[str, List[str]]],
    selected_load_cases: Set[str],
) -> Dict[str, Dict[str, List[str]]]:
    """Detect conflicting load cases (same sheet + load case appearing in multiple files)."""
    conflicts: Dict[str, Dict[str, List[str]]] = {}
    sheet_types = {sheet for sheets in file_load_cases.values() for sheet in sheets.keys()}

    for sheet_name in sheet_types:
        lc_files: Dict[str, List[str]] = defaultdict(list)
        for file_name, sheets in file_load_cases.items():
            if sheet_name not in sheets:
                continue
            for load_case in sheets[sheet_name]:
                if load_case in selected_load_cases:
                    lc_files[load_case].append(file_name)
        for load_case, files in lc_files.items():
            if len(files) > 1:
                conflicts.setdefault(load_case, {})[sheet_name] = files
    return conflicts


def determine_allowed_load_cases(
    file_name: str,
    file_sheets: Dict[str, List[str]],
    selected_load_cases: Set[str],
    resolution: Dict[str, Dict[str, Optional[str]]],
    already_imported: Dict[str, Set[str]],
) -> Tuple[Set[str], Dict[str, List[str]]]:
    """Decide which load cases can be imported for a single file."""
    allowed: Set[str] = set()
    skipped_by_sheet: Dict[str, List[str]] = defaultdict(list)

    for sheet_name, load_cases_in_sheet in file_sheets.items():
        imported_for_sheet = already_imported.get(sheet_name, set())
        resolution_for_sheet = resolution.get(sheet_name, {})

        for load_case in load_cases_in_sheet:
            if load_case not in selected_load_cases:
                continue

            if load_case in resolution_for_sheet:
                chosen_file = resolution_for_sheet[load_case]
                if chosen_file is None:
                    skipped_by_sheet[sheet_name].append(f"{load_case} (user skipped)")
                elif chosen_file == file_name:
                    allowed.add(load_case)
                else:
                    skipped_by_sheet[sheet_name].append(f"{load_case} (using {chosen_file})")
                continue

            if load_case in imported_for_sheet:
                skipped_by_sheet[sheet_name].append(f"{load_case} (already imported)")
                continue

            allowed.add(load_case)

    return allowed, skipped_by_sheet
