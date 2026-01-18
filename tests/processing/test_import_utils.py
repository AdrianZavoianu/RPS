from processing.import_utils import require_sheets, any_sheet_available, all_sheets_available


def test_require_sheets_respects_require_all():
    validator = lambda name: name in {"A", "B"}

    assert require_sheets(["A", "B"], validator, require_all=True) is True
    assert require_sheets(["A", "C"], validator, require_all=True) is False
    assert require_sheets(["C", "B"], validator, require_all=False) is True
    assert require_sheets(["C", "D"], validator, require_all=False) is False


def test_any_all_helpers():
    validator = lambda name: name == "X"
    assert any_sheet_available(["X", "Y"], validator) is True
    assert any_sheet_available(["A", "B"], validator) is False
    assert all_sheets_available(["X", "Y"], validator) is False
    assert all_sheets_available(["X"], validator) is True
