"""Export worker threads for background export operations.

These workers run exports in separate threads to prevent UI freezing.
"""

from datetime import datetime
from PyQt6.QtCore import QThread, pyqtSignal

from services.export_service import ExportService, ExportOptions
from services.export_utils import extract_direction, extract_base_type, get_result_config


class ComprehensiveExportWorker(QThread):
    """Background worker for comprehensive export operations."""

    progress = pyqtSignal(str, int, int)
    finished = pyqtSignal(bool, str, str)  # success, message, output_path

    def __init__(self, context, result_service, result_set_ids, result_types,
                 format_type, is_combined, output_file, output_folder, analysis_context='NLTHA'):
        super().__init__()
        self.context = context
        self.result_service = result_service
        self.result_set_ids = result_set_ids
        self.result_types = result_types
        self.format_type = format_type
        self.is_combined = is_combined
        self.output_file = output_file
        self.output_folder = output_folder
        self.analysis_context = analysis_context

    def run(self):
        """Execute comprehensive export."""
        try:
            if self.is_combined:
                self._export_combined()
            else:
                self._export_per_file()
        except Exception as e:
            import traceback
            traceback.print_exc()
            self.finished.emit(False, f"Export failed: {str(e)}", "")

    def _export_combined(self):
        """Export all result types from all result sets to single Excel file."""
        import pandas as pd
        from database.repository import ResultSetRepository

        # Calculate total operations
        total_operations = len(self.result_types) * len(self.result_set_ids)
        current_operation = 0

        self.progress.emit("Preparing combined export...", 0, total_operations)

        export_service = ExportService(self.context, self.result_service)
        exported_count = 0
        skipped = []

        # Get result set names
        with self.context.session() as session:
            result_set_repo = ResultSetRepository(session)
            result_set_names = {}
            for rs_id in self.result_set_ids:
                rs = result_set_repo.get_by_id(rs_id)
                if rs:
                    result_set_names[rs_id] = rs.name

        # Generate single timestamp for this export
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        with pd.ExcelWriter(self.output_file, engine='openpyxl') as writer:
            for result_set_id in self.result_set_ids:
                result_set_name = result_set_names.get(result_set_id, f"RS{result_set_id}")

                for result_type in self.result_types:
                    current_operation += 1
                    self.progress.emit(
                        f"Exporting {result_set_name} - {result_type}...",
                        current_operation,
                        total_operations
                    )

                    try:
                        # Special handling for pushover curves
                        if result_type == "Curves":
                            # Export pushover curves to separate sheets (one per case)
                            from database.repository import PushoverCaseRepository

                            with self.context.session() as session:
                                pushover_repo = PushoverCaseRepository(session)
                                cases = pushover_repo.get_by_result_set(result_set_id)

                                for case in cases:
                                    curve_points = pushover_repo.get_curve_data(case.id)

                                    if not curve_points:
                                        continue

                                    # Build DataFrame for this curve
                                    data = {
                                        'Step Number': [pt.step_number for pt in curve_points],
                                        'Base Shear (kN)': [pt.base_shear for pt in curve_points],
                                        'Displacement (mm)': [pt.displacement for pt in curve_points]
                                    }
                                    df = pd.DataFrame(data)

                                    # Sheet name: ResultSetName_CaseName (truncate to 31 chars)
                                    sheet_name = f"{result_set_name}_{case.name}"[:31]
                                    df.to_excel(writer, sheet_name=sheet_name, index=False)
                                    exported_count += 1

                            continue  # Move to next result type

                        # Determine if this is a global, element, or joint result
                        is_element = any(x in result_type for x in ['Wall', 'Quad', 'Column', 'Beam'])
                        is_joint = any(x in result_type for x in ['SoilPressures', 'VerticalDisplacements', 'JointDisplacements'])
                        is_pushover = self.analysis_context == 'Pushover'

                        if is_element:
                            # Get combined element data
                            df = export_service.get_element_export_dataframe(
                                result_type=result_type,
                                result_set_id=result_set_id,
                                is_pushover=is_pushover
                            )

                            if df is None or df.empty:
                                skipped.append(f"{result_set_name}_{result_type}")
                                continue

                            # Write to sheet with result set name prefix
                            sheet_name = f"{result_set_name}_{result_type}"[:31]
                            df.to_excel(writer, sheet_name=sheet_name, index=False)
                            exported_count += 1

                        elif is_joint:
                            # Get joint result data
                            # result_type already includes _Min suffix from _get_selected_result_types()
                            dataset = self.result_service.get_joint_dataset(
                                result_type=result_type,
                                result_set_id=result_set_id,
                                is_pushover=is_pushover
                            )

                            if dataset is None or dataset.data is None or dataset.data.empty:
                                skipped.append(f"{result_set_name}_{result_type}")
                                continue

                            # Write to sheet (remove _Min from sheet name for cleaner display)
                            display_type = result_type.replace('_Min', '')
                            sheet_name = f"{result_set_name}_{display_type}"[:31]
                            dataset.data.to_excel(writer, sheet_name=sheet_name, index=False)
                            exported_count += 1

                        else:
                            # Get global result data
                            config = get_result_config(result_type)
                            direction = extract_direction(result_type, config)
                            base_type = extract_base_type(result_type)

                            dataset = self.result_service.get_standard_dataset(
                                result_type=base_type,
                                direction=direction,
                                result_set_id=result_set_id,
                                is_pushover=is_pushover
                            )

                            if dataset is None or dataset.data is None or dataset.data.empty:
                                skipped.append(f"{result_set_name}_{result_type}")
                                continue

                            # Write to sheet with result set name prefix
                            sheet_name = f"{result_set_name}_{result_type}"[:31]
                            export_df = export_service.prepare_dataset_for_export(dataset, result_type)
                            (export_df if export_df is not None else dataset.data).to_excel(
                                writer, sheet_name=sheet_name, index=False
                            )
                            exported_count += 1

                    except Exception as e:
                        print(f"Error exporting {result_set_name} - {result_type}: {str(e)}")
                        import traceback
                        traceback.print_exc()
                        skipped.append(f"{result_set_name}_{result_type}")
                        continue

        # Build success message
        message = f"Successfully exported {exported_count} sheets ({len(self.result_set_ids)} result sets × {len(self.result_types)} result types)!"
        if skipped:
            message += f"\n\nSkipped {len(skipped)} items (no data): {', '.join(skipped[:5])}"
            if len(skipped) > 5:
                message += f" and {len(skipped) - 5} more..."

        self.finished.emit(True, message, str(self.output_file))

    def _export_per_file(self):
        """Export results to files.

        For Excel format: Creates one Excel file per result set (all types as sheets).
        For CSV format: Creates one CSV file per result type per result set.
        """
        import pandas as pd
        from database.repository import ResultSetRepository

        self.output_folder.mkdir(parents=True, exist_ok=True)

        # Generate single timestamp for this export
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # Get result set names
        with self.context.session() as session:
            result_set_repo = ResultSetRepository(session)
            result_set_names = {}
            for rs_id in self.result_set_ids:
                rs = result_set_repo.get_by_id(rs_id)
                if rs:
                    result_set_names[rs_id] = rs.name

        if self.format_type == "excel":
            # Excel: One file per result set with all types as sheets
            self._export_excel_per_result_set(result_set_names, timestamp)
        else:
            # CSV: One file per result type per result set
            self._export_csv_per_file(result_set_names, timestamp)

    def _export_excel_per_result_set(self, result_set_names, timestamp):
        """Export one Excel file per result set with all result types as sheets."""
        import pandas as pd
        from database.repository import PushoverCaseRepository

        export_service = ExportService(self.context, self.result_service)

        # Calculate total operations (one per result set)
        total_operations = len(self.result_set_ids)
        current_operation = 0

        exported_count = 0
        skipped = []

        self.progress.emit("Preparing export...", 0, total_operations)

        for result_set_id in self.result_set_ids:
            current_operation += 1
            result_set_name = result_set_names.get(result_set_id, f"RS{result_set_id}")

            self.progress.emit(
                f"Exporting {result_set_name}...",
                current_operation,
                total_operations
            )

            # Build output path for this result set
            filename = f"{result_set_name}_{self.analysis_context}_Results_{timestamp}.xlsx"
            output_path = self.output_folder / filename

            sheets_written = 0

            try:
                with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
                    for result_type in self.result_types:
                        try:
                            # Special handling for pushover curves
                            if result_type == "Curves":
                                with self.context.session() as session:
                                    pushover_repo = PushoverCaseRepository(session)
                                    cases = pushover_repo.get_by_result_set(result_set_id)

                                    for case in cases:
                                        curve_points = pushover_repo.get_curve_data(case.id)

                                        if not curve_points:
                                            continue

                                        # Build DataFrame for this curve
                                        data = {
                                            'Step Number': [pt.step_number for pt in curve_points],
                                            'Base Shear (kN)': [pt.base_shear for pt in curve_points],
                                            'Displacement (mm)': [pt.displacement for pt in curve_points]
                                        }
                                        df = pd.DataFrame(data)

                                        # Sheet name: "Curve_CaseName" (truncate to 31 chars)
                                        sheet_name = f"Curve_{case.name}"[:31]
                                        df.to_excel(writer, sheet_name=sheet_name, index=False)
                                        sheets_written += 1

                                continue  # Move to next result type

                            # Determine if this is a global, element, or joint result
                            is_element = any(x in result_type for x in ['Wall', 'Quad', 'Column', 'Beam'])
                            is_joint = any(x in result_type for x in ['SoilPressures', 'VerticalDisplacements', 'JointDisplacements'])
                            is_pushover = self.analysis_context == 'Pushover'

                            if is_element:
                                # Get combined element data
                                df = export_service.get_element_export_dataframe(
                                    result_type=result_type,
                                    result_set_id=result_set_id,
                                    is_pushover=is_pushover
                                )

                                if df is None or df.empty:
                                    continue

                                # Sheet name: result type (truncate to 31 chars)
                                sheet_name = result_type[:31]
                                df.to_excel(writer, sheet_name=sheet_name, index=False)
                                sheets_written += 1

                            elif is_joint:
                                # Get joint result data
                                dataset = self.result_service.get_joint_dataset(
                                    result_type=result_type,
                                    result_set_id=result_set_id,
                                    is_pushover=is_pushover
                                )

                                if dataset is None or dataset.data is None or dataset.data.empty:
                                    continue

                                # Sheet name: clean type without _Min (truncate to 31 chars)
                                display_type = result_type.replace('_Min', '')
                                sheet_name = display_type[:31]
                                dataset.data.to_excel(writer, sheet_name=sheet_name, index=False)
                                sheets_written += 1

                            else:
                                # Get global result data
                                config = get_result_config(result_type)
                                direction = extract_direction(result_type, config)
                                base_type = extract_base_type(result_type)

                                dataset = self.result_service.get_standard_dataset(
                                    result_type=base_type,
                                    direction=direction,
                                    result_set_id=result_set_id,
                                    is_pushover=is_pushover
                                )

                                if dataset is None or dataset.data is None or dataset.data.empty:
                                    continue

                                # Sheet name: result type (truncate to 31 chars)
                                sheet_name = result_type[:31]
                                export_df = export_service.prepare_dataset_for_export(dataset, result_type)
                                (export_df if export_df is not None else dataset.data).to_excel(
                                    writer, sheet_name=sheet_name, index=False
                                )
                                sheets_written += 1

                        except Exception as e:
                            print(f"Error exporting {result_set_name} - {result_type}: {str(e)}")
                            import traceback
                            traceback.print_exc()
                            continue

                if sheets_written > 0:
                    exported_count += 1
                else:
                    skipped.append(result_set_name)
                    # Remove empty file
                    if output_path.exists():
                        output_path.unlink()

            except Exception as e:
                print(f"Error creating Excel file for {result_set_name}: {str(e)}")
                import traceback
                traceback.print_exc()
                skipped.append(result_set_name)

        # Build success message
        message = f"Successfully exported {exported_count} Excel file(s) with {len(self.result_types)} result type(s) each!"
        if skipped:
            message += f"\n\nSkipped {len(skipped)} result set(s) (no data): {', '.join(skipped[:5])}"
            if len(skipped) > 5:
                message += f" and {len(skipped) - 5} more..."

        self.finished.emit(True, message, str(self.output_folder))

    def _export_csv_per_file(self, result_set_names, timestamp):
        """Export one CSV file per result type per result set."""
        import pandas as pd

        export_service = ExportService(self.context, self.result_service)

        # Calculate total operations
        total_operations = len(self.result_types) * len(self.result_set_ids)
        current_operation = 0

        self.progress.emit("Preparing export folder...", 0, total_operations)

        exported_count = 0
        skipped = []

        for result_set_id in self.result_set_ids:
            result_set_name = result_set_names.get(result_set_id, f"RS{result_set_id}")

            for result_type in self.result_types:
                current_operation += 1
                self.progress.emit(
                    f"Exporting {result_set_name} - {result_type}...",
                    current_operation,
                    total_operations
                )

                try:
                    # Skip curves for CSV (not supported)
                    if result_type == "Curves":
                        skipped.append(f"{result_set_name}_Curves (CSV not supported)")
                        continue

                    # Determine if this is a global, element, or joint result
                    is_element = any(x in result_type for x in ['Wall', 'Quad', 'Column', 'Beam'])
                    is_joint = any(x in result_type for x in ['SoilPressures', 'VerticalDisplacements', 'JointDisplacements'])

                    # Build output path with single timestamp
                    display_type = result_type.replace('_Min', '') if is_joint else result_type
                    filename = f"{result_set_name}_{self.analysis_context}_{display_type}_{timestamp}.csv"
                    output_path = self.output_folder / filename

                    if is_element:
                        df = export_service.get_element_export_dataframe(
                            result_type=result_type,
                            result_set_id=result_set_id
                        )

                        if df is None or df.empty:
                            skipped.append(f"{result_set_name}_{result_type}")
                            continue

                        df.to_csv(output_path, index=False)
                        exported_count += 1

                    elif is_joint:
                        dataset = self.result_service.get_joint_dataset(
                            result_type=result_type,
                            result_set_id=result_set_id
                        )

                        if dataset is None or dataset.data is None or dataset.data.empty:
                            skipped.append(f"{result_set_name}_{result_type}")
                            continue

                        dataset.data.to_csv(output_path, index=False)
                        exported_count += 1

                    else:
                        # Export using service (for global results)
                        options = ExportOptions(
                            result_set_id=result_set_id,
                            result_type=result_type,
                            output_path=output_path,
                            format="csv"
                        )

                        export_service.export_result_type(options)
                        exported_count += 1

                except Exception as e:
                    print(f"Error exporting {result_set_name} - {result_type}: {str(e)}")
                    import traceback
                    traceback.print_exc()
                    skipped.append(f"{result_set_name}_{result_type}")
                    continue

        # Build success message
        message = f"Successfully exported {exported_count} CSV file(s)!"
        if skipped:
            message += f"\n\nSkipped {len(skipped)} items (no data): {', '.join(skipped[:5])}"
            if len(skipped) > 5:
                message += f" and {len(skipped) - 5} more..."

        self.finished.emit(True, message, str(self.output_folder))


class ExportWorker(QThread):
    """Background worker for executing simple export operations.

    Runs export in separate thread to prevent UI freezing.

    Signals:
        progress: Emitted with (message, current, total) during export
        finished: Emitted with (success, message) when complete
    """

    progress = pyqtSignal(str, int, int)
    finished = pyqtSignal(bool, str)

    def __init__(self, context, result_service, options: ExportOptions):
        """Initialize export worker.

        Args:
            context: ProjectContext instance
            result_service: ResultDataService instance
            options: ExportOptions specifying what to export
        """
        super().__init__()
        self.context = context
        self.result_service = result_service
        self.options = options

    def run(self):
        """Execute export in background thread."""
        try:
            export_service = ExportService(self.context, self.result_service)

            export_service.export_result_type(
                self.options,
                progress_callback=self._emit_progress
            )

            file_format = "Excel" if self.options.format == "excel" else "CSV"
            self.finished.emit(
                True,
                f"Successfully exported {self.options.result_type} to {file_format} file!"
            )

        except Exception as e:
            self.finished.emit(
                False,
                f"Export failed: {str(e)}"
            )

    def _emit_progress(self, message: str, current: int, total: int):
        """Emit progress signal.

        Args:
            message: Progress message
            current: Current step number
            total: Total number of steps
        """
        self.progress.emit(message, current, total)


class ExportProjectExcelWorker(QThread):
    """Background worker for Excel project export."""

    progress = pyqtSignal(str, int, int)
    finished = pyqtSignal(bool, str, str)

    def __init__(self, context, result_service, options):
        super().__init__()
        self.context = context
        self.result_service = result_service
        self.options = options

    def run(self):
        try:
            from services.export_service import ExportService

            export_service = ExportService(self.context, self.result_service)

            export_service.export_project_excel(
                self.options,
                progress_callback=self._emit_progress
            )

            self.finished.emit(
                True,
                "Project exported successfully to Excel!",
                str(self.options.output_path)
            )
        except Exception as e:
            import traceback
            traceback.print_exc()
            self.finished.emit(False, f"Export failed: {str(e)}", "")

    def _emit_progress(self, message: str, current: int, total: int):
        self.progress.emit(message, current, total)
