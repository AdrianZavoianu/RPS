import pandas as pd

from services.export_writer import ExportWriter


def test_export_writer_writes_excel_and_csv(tmp_path):
    df = pd.DataFrame([{"a": 1, "b": "x"}])
    writer = ExportWriter()

    excel_path = tmp_path / "out.xlsx"
    csv_path = tmp_path / "out.csv"

    writer.write_dataset(df, excel_path, "excel")
    writer.write_dataset(df, csv_path, "csv")

    # Files should exist and be non-empty
    assert excel_path.exists() and excel_path.stat().st_size > 0
    assert csv_path.exists() and csv_path.stat().st_size > 0
