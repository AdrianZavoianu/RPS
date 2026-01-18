from importlib import util
from pathlib import Path


def _load_hygiene_module():
    root = Path(__file__).parent.parent
    module_path = root / "scripts" / "check_repo_hygiene.py"
    spec = util.spec_from_file_location("check_repo_hygiene", module_path)
    module = util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)  # type: ignore[attr-defined]
    return module


def test_repo_hygiene_script_passes_for_current_tree():
    mod = _load_hygiene_module()
    assert mod.main() == 0
