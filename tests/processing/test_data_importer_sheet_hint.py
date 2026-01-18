from processing.data_importer import DataImporter


class StubParser:
    def validate_sheet_exists(self, name: str) -> bool:
        raise AssertionError("Should not call parser when hint provided")


class StubSummary:
    def __init__(self, available_sheets):
        self.available_sheets = available_sheets


def test_sheet_availability_prefers_prescan_hint(tmp_path):
    dummy_file = tmp_path / "fake.xlsx"
    dummy_file.write_text("", encoding="utf-8")

    importer = DataImporter(
        file_path=str(dummy_file),
        project_name="P",
        result_set_name="RS",
        session_factory=lambda: None,
        result_types=[],
        file_summary=StubSummary({"Foo", "Bar"}),
    )
    importer.parser = StubParser()

    assert importer._sheet_available("Foo") is True
    assert importer._sheet_available("Missing") is False
