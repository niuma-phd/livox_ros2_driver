import importlib.util
import json
from pathlib import Path

import pytest


SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "configure_broadcast.py"


def _load_script():
    spec = importlib.util.spec_from_file_location("configure_broadcast", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_horizon_without_code_keeps_empty_safe_default():
    module = _load_script()
    assert module.build_config("horizon", None)["lidar_config"] == []


def test_avia_without_code_keeps_disabled_placeholder():
    module = _load_script()
    lidar = module.build_config("avia", None)["lidar_config"]
    assert lidar == [module.lidar_entry("0" * 15, enabled=False)]


def test_valid_code_enables_exact_selected_device_for_both_models():
    module = _load_script()
    for model in ("horizon", "avia"):
        lidar = module.build_config(model, "TESTCODE0000000")["lidar_config"]
        assert lidar == [module.lidar_entry("TESTCODE0000000", enabled=True)]


@pytest.mark.parametrize("code", ["short", "1234567890123456", "12345678901234-", "测试0000000000000"])
def test_invalid_broadcast_codes_are_rejected(code):
    module = _load_script()
    with pytest.raises(ValueError, match="15 ASCII alphanumeric"):
        module.validate_broadcast_code(code)


def test_cli_writes_json(tmp_path):
    module = _load_script()
    output = tmp_path / "horizon.json"
    assert module.main(["horizon", "TESTCODE0000000", "--output", str(output)]) == 0
    assert json.loads(output.read_text())["lidar_config"][0]["enable_connect"] is True


def test_cli_defaults_to_ignored_site_config_in_current_workspace(tmp_path, monkeypatch):
    module = _load_script()
    monkeypatch.chdir(tmp_path)
    assert module.main(["avia", "TESTCODE0000000"]) == 0
    output = tmp_path / "site_config" / "avia.json"
    assert json.loads(output.read_text())["lidar_config"][0]["broadcast_code"] == (
        "TESTCODE0000000"
    )
