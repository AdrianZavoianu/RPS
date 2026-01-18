from utils.timing import PhaseTimer


def test_phase_timer_records_phase_and_context():
    timer = PhaseTimer({"file": "example.xlsx"})

    with timer.measure("parse", {"sheet": "Drifts"}):
        pass

    with timer.measure("cache_build"):
        pass

    entries = timer.as_list()
    assert len(entries) == 2

    first, second = entries
    assert first["phase"] == "parse"
    assert first["file"] == "example.xlsx"
    assert first["sheet"] == "Drifts"
    assert first["duration"] >= 0

    assert second["phase"] == "cache_build"
    assert second["file"] == "example.xlsx"
    assert "sheet" not in second
