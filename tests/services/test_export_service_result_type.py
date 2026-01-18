from pathlib import Path

import pandas as pd

from services.export_service import ExportService, ExportOptions


class _Dataset:
    def __init__(self, df: pd.DataFrame):
        self.data = df


class _ResultServiceStub:
    def __init__(self, df: pd.DataFrame):
        self._df = df

    def get_standard_dataset(self, result_type: str, direction: str, result_set_id: int):
        # Return static dataset regardless of params for the test
        return _Dataset(self._df)


class _ContextStub:
    def session(self):
        raise RuntimeError("session should not be called in export_result_type test")

    def session_factory(self):
        return self.session


def test_export_result_type_writes_file(tmp_path):
    df = pd.DataFrame([{"Story": "S1", "LC1": 0.1}])
    result_service = _ResultServiceStub(df)
    ctx = _ContextStub()
    svc = ExportService(ctx, result_service)

    output = tmp_path / "out.xlsx"
    opts = ExportOptions(
        result_set_id=1,
        result_type="Drifts_X",
        output_path=output,
        format="excel",
    )

    svc.export_result_type(opts)

    assert output.exists() and output.stat().st_size > 0
