"""Tests for pushover importer factory."""

import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch

from processing.pushover_importer_factory import (
    IMPORTER_REGISTRY,
    get_importer_class,
    create_importer,
    get_available_importers,
    get_element_importers,
    get_joint_importers,
    get_global_importers,
    import_multiple,
)


class TestImporterRegistry:
    """Tests for the importer registry."""

    def test_registry_contains_element_importers(self):
        """Test that registry contains element importers."""
        assert "wall" in IMPORTER_REGISTRY
        assert "column_rotation" in IMPORTER_REGISTRY
        assert "column_shear" in IMPORTER_REGISTRY
        assert "beam_rotation" in IMPORTER_REGISTRY

    def test_registry_contains_joint_importers(self):
        """Test that registry contains joint importers."""
        assert "joint_displacement" in IMPORTER_REGISTRY
        assert "soil_pressure" in IMPORTER_REGISTRY
        assert "vertical_displacement" in IMPORTER_REGISTRY

    def test_registry_contains_global_importers(self):
        """Test that registry contains global importers."""
        assert "global" in IMPORTER_REGISTRY
        assert "curve" in IMPORTER_REGISTRY

    def test_registry_entries_have_correct_format(self):
        """Test that registry entries are (module_path, class_name) tuples."""
        for key, value in IMPORTER_REGISTRY.items():
            assert isinstance(value, tuple), f"Entry for {key} is not a tuple"
            assert len(value) == 2, f"Entry for {key} doesn't have 2 elements"
            module_path, class_name = value
            assert isinstance(module_path, str), f"Module path for {key} is not a string"
            assert isinstance(class_name, str), f"Class name for {key} is not a string"
            assert module_path.startswith("processing."), f"Module path for {key} doesn't start with 'processing.'"


class TestGetImporterClass:
    """Tests for get_importer_class function."""

    def test_raises_key_error_for_unknown_type(self):
        """Test that KeyError is raised for unknown importer type."""
        with pytest.raises(KeyError) as exc_info:
            get_importer_class("unknown_type")

        assert "Unknown importer type" in str(exc_info.value)
        assert "unknown_type" in str(exc_info.value)

    def test_error_message_lists_available_types(self):
        """Test that error message lists available types."""
        with pytest.raises(KeyError) as exc_info:
            get_importer_class("unknown")

        error_msg = str(exc_info.value)
        assert "Available:" in error_msg
        # Check some known types are listed
        assert "wall" in error_msg
        assert "curve" in error_msg

    def test_loads_curve_importer(self):
        """Test that curve importer can be loaded."""
        importer_class = get_importer_class("curve")
        assert importer_class.__name__ == "PushoverImporter"

    def test_loads_wall_importer(self):
        """Test that wall importer can be loaded."""
        importer_class = get_importer_class("wall")
        # V2 importer class name, aliased as PushoverWallImporter
        assert "PushoverWallImporter" in importer_class.__name__

    def test_raises_import_error_for_bad_module(self):
        """Test that ImportError is raised if module doesn't exist."""
        # Temporarily add a bad entry
        original = IMPORTER_REGISTRY.copy()
        IMPORTER_REGISTRY["bad_import"] = ("processing.nonexistent_module", "FakeClass")

        try:
            with pytest.raises(ImportError) as exc_info:
                get_importer_class("bad_import")

            assert "Failed to load importer" in str(exc_info.value)
        finally:
            # Restore registry
            IMPORTER_REGISTRY.clear()
            IMPORTER_REGISTRY.update(original)


class TestCreateImporter:
    """Tests for create_importer function."""

    def test_creates_importer_instance(self):
        """Test that create_importer returns an instance of the importer."""
        mock_session = MagicMock()

        # Use curve importer as it's simpler
        with patch("processing.pushover_importer_factory.get_importer_class") as mock_get_class:
            mock_importer_class = MagicMock()
            mock_instance = MagicMock()
            mock_importer_class.return_value = mock_instance
            mock_get_class.return_value = mock_importer_class

            result = create_importer(
                importer_type="curve",
                project_id=1,
                session=mock_session,
                result_set_id=10,
                file_path=Path("test.xlsx"),
                selected_load_cases_x=["PX1"],
                selected_load_cases_y=["PY1"],
            )

            assert result is mock_instance
            mock_importer_class.assert_called_once()

    def test_passes_all_arguments_to_importer(self):
        """Test that all arguments are passed to the importer class."""
        mock_session = MagicMock()
        mock_callback = MagicMock()
        file_path = Path("test.xlsx")

        with patch("processing.pushover_importer_factory.get_importer_class") as mock_get_class:
            mock_importer_class = MagicMock()
            mock_get_class.return_value = mock_importer_class

            create_importer(
                importer_type="wall",
                project_id=42,
                session=mock_session,
                result_set_id=100,
                file_path=file_path,
                selected_load_cases_x=["PX1", "PX2"],
                selected_load_cases_y=["PY1"],
                progress_callback=mock_callback,
            )

            mock_importer_class.assert_called_once_with(
                project_id=42,
                session=mock_session,
                result_set_id=100,
                file_path=file_path,
                selected_load_cases_x=["PX1", "PX2"],
                selected_load_cases_y=["PY1"],
                progress_callback=mock_callback,
            )


class TestHelperFunctions:
    """Tests for helper functions."""

    def test_get_available_importers_returns_sorted_list(self):
        """Test that get_available_importers returns sorted list."""
        result = get_available_importers()
        assert isinstance(result, list)
        assert result == sorted(result)
        assert len(result) == len(IMPORTER_REGISTRY)

    def test_get_element_importers(self):
        """Test get_element_importers returns correct list."""
        result = get_element_importers()
        assert "wall" in result
        assert "column_rotation" in result
        assert "column_shear" in result
        assert "beam_rotation" in result
        assert len(result) == 4

    def test_get_joint_importers(self):
        """Test get_joint_importers returns correct list."""
        result = get_joint_importers()
        assert "joint_displacement" in result
        assert "soil_pressure" in result
        assert "vertical_displacement" in result
        assert len(result) == 3

    def test_get_global_importers(self):
        """Test get_global_importers returns correct list."""
        result = get_global_importers()
        assert "global" in result
        assert "curve" in result
        assert len(result) == 2


class TestImportMultiple:
    """Tests for import_multiple function."""

    def test_skips_types_without_file_paths(self):
        """Test that types without file paths are skipped."""
        mock_session = MagicMock()

        with patch("processing.pushover_importer_factory.create_importer") as mock_create:
            with patch("processing.pushover_importer_factory.logger") as mock_logger:
                result = import_multiple(
                    importer_types=["wall", "beam_rotation"],
                    project_id=1,
                    session=mock_session,
                    result_set_id=10,
                    file_paths={"wall": Path("wall.xlsx")},  # Missing beam_rotation
                    selected_load_cases_x=["PX1"],
                    selected_load_cases_y=["PY1"],
                )

                # Should only create wall importer
                assert mock_create.call_count == 1
                # Should log warning about missing beam_rotation
                mock_logger.warning.assert_called()

    def test_calls_progress_callback(self):
        """Test that progress callback is called."""
        mock_session = MagicMock()
        mock_callback = MagicMock()

        with patch("processing.pushover_importer_factory.create_importer") as mock_create:
            mock_importer = MagicMock()
            mock_importer.import_all.return_value = {"records": 10}
            mock_create.return_value = mock_importer

            import_multiple(
                importer_types=["wall"],
                project_id=1,
                session=mock_session,
                result_set_id=10,
                file_paths={"wall": Path("wall.xlsx")},
                selected_load_cases_x=["PX1"],
                selected_load_cases_y=["PY1"],
                progress_callback=mock_callback,
            )

            # Should call progress at start and end
            assert mock_callback.call_count >= 2
            # Last call should be "Import complete"
            last_call = mock_callback.call_args_list[-1]
            assert "complete" in last_call[0][0].lower()

    def test_returns_results_from_each_importer(self):
        """Test that results from each importer are returned."""
        mock_session = MagicMock()

        with patch("processing.pushover_importer_factory.create_importer") as mock_create:
            mock_importer = MagicMock()
            mock_importer.import_all.return_value = {"records": 10, "success": True}
            mock_create.return_value = mock_importer

            result = import_multiple(
                importer_types=["wall", "beam_rotation"],
                project_id=1,
                session=mock_session,
                result_set_id=10,
                file_paths={
                    "wall": Path("wall.xlsx"),
                    "beam_rotation": Path("beam.xlsx"),
                },
                selected_load_cases_x=["PX1"],
                selected_load_cases_y=["PY1"],
            )

            assert "wall" in result
            assert "beam_rotation" in result
            assert result["wall"]["records"] == 10

    def test_captures_import_errors(self):
        """Test that import errors are captured in results."""
        mock_session = MagicMock()

        with patch("processing.pushover_importer_factory.create_importer") as mock_create:
            mock_create.side_effect = ValueError("Import failed")

            result = import_multiple(
                importer_types=["wall"],
                project_id=1,
                session=mock_session,
                result_set_id=10,
                file_paths={"wall": Path("wall.xlsx")},
                selected_load_cases_x=["PX1"],
                selected_load_cases_y=["PY1"],
            )

            assert "wall" in result
            assert "error" in result["wall"]
            assert "Import failed" in result["wall"]["error"]

    def test_continues_after_error(self):
        """Test that processing continues after an error."""
        mock_session = MagicMock()

        with patch("processing.pushover_importer_factory.create_importer") as mock_create:
            # First call fails, second succeeds
            def side_effect(*args, **kwargs):
                if kwargs.get("importer_type") == "wall":
                    raise ValueError("Wall import failed")
                mock_importer = MagicMock()
                mock_importer.import_all.return_value = {"records": 5}
                return mock_importer

            mock_create.side_effect = side_effect

            result = import_multiple(
                importer_types=["wall", "beam_rotation"],
                project_id=1,
                session=mock_session,
                result_set_id=10,
                file_paths={
                    "wall": Path("wall.xlsx"),
                    "beam_rotation": Path("beam.xlsx"),
                },
                selected_load_cases_x=["PX1"],
                selected_load_cases_y=["PY1"],
            )

            # Both should be in results
            assert "wall" in result
            assert "beam_rotation" in result
            # Wall should have error
            assert "error" in result["wall"]
            # Beam should have successful result
            assert result["beam_rotation"]["records"] == 5
