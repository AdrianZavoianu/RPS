from config.result_config import format_result_type_with_unit


def test_column_axials_title_omits_direction_and_uses_min_max_labels():
    """Column axial titles should not append a direction suffix."""
    label_min = format_result_type_with_unit("ColumnAxials", "Min")
    label_max = format_result_type_with_unit("ColumnAxials", "Max")

    assert label_min == "Min Axial Force [kN]"
    assert label_max == "Max Axial Force [kN]"
    assert "Direction" not in label_min
    assert "Direction" not in label_max
