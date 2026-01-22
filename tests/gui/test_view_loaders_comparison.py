import pandas as pd

from gui.project_detail import view_loaders


class DummyWidget:
    def __init__(self):
        self.loaded = False
        self.datasets = None
        self.result_type = None
        self.cleared = False
        self.x_label = None

    def load_comparison_datasets(self, datasets, result_type=None):
        self.loaded = True
        self.datasets = datasets
        self.result_type = result_type

    def set_x_label(self, label):
        self.x_label = label

    def clear_data(self):
        self.cleared = True


class DummyTitle:
    def __init__(self):
        self.text = ""

    def setText(self, text):
        self.text = text


class DummyArea:
    def __init__(self):
        self.comparison_joint_scatter_widget = DummyWidget()
        self.comparison_all_rotations_widget = DummyWidget()
        self.content_title = DummyTitle()
        self.show_called = False

    def show_comparison_scatter(self):
        self.show_called = True

    def show_comparison_rotations(self):
        self.show_called = True


class DummyComparisonSet:
    def __init__(self, result_set_ids):
        self.result_set_ids = result_set_ids


class DummyWindow:
    def __init__(self):
        self.session = object()

        class StatusBar:
            def __init__(self):
                self.message = ""

            def showMessage(self, msg):
                self.message = msg

        self._status = StatusBar()

    def statusBar(self):
        return self._status


class RepoStub:
    def __init__(self, _session=None):
        pass

    def get_by_id(self, result_set_id):
        return type("ResultSet", (), {"id": result_set_id, "name": f"RS{result_set_id}"})()


def test_load_comparison_joint_scatter_shows_view(monkeypatch):
    """Ensure comparison joint scatter view is shown and fed datasets."""
    area = DummyArea()
    window = DummyWindow()
    comparison_set = DummyComparisonSet([1, 2])

    df = pd.DataFrame({"Shell Object": ["F1"], "Unique Name": ["F1"], "TH01": [-10.0]})
    datasets = [("DES", df, ["TH01"]), ("MCE", df, ["TH01"])]

    import database.repository as repo_module
    import services.result_service.comparison_builder as comparison_builder

    monkeypatch.setattr(repo_module, "ResultSetRepository", RepoStub)
    monkeypatch.setattr(comparison_builder, "build_all_joints_comparison", lambda **_: datasets)

    view_loaders.load_comparison_joint_scatter(
        window, comparison_set, "SoilPressures", area
    )

    assert area.show_called
    assert area.comparison_joint_scatter_widget.loaded
    assert area.comparison_joint_scatter_widget.datasets == datasets
    assert "Comparison" in area.content_title.text


def test_load_comparison_all_beam_rotations(monkeypatch):
    """Ensure beam rotation comparison loads all beams across sets."""
    area = DummyArea()
    window = DummyWindow()
    comparison_set = DummyComparisonSet([1, 2])

    df = pd.DataFrame({"Element": ["B1"], "Story": ["L1"], "Rotation": [0.5]})

    import database.repository as repo_module

    class RepoStubLocal:
        def __init__(self, _session=None):
            pass

        def get_by_id(self, rid):
            return type("ResultSet", (), {"id": rid, "name": f"RS{rid}"})()

    monkeypatch.setattr(repo_module, "ResultSetRepository", RepoStubLocal)

    window.result_service = type(
        "RS",
        (),
        {"get_all_beam_rotations_dataset": staticmethod(lambda _rs_id, _mm=None: df)},
    )

    view_loaders.load_comparison_all_beam_rotations(window, comparison_set, area)

    assert area.show_called
    assert area.comparison_all_rotations_widget.loaded
    assert len(area.comparison_all_rotations_widget.datasets) == 2
