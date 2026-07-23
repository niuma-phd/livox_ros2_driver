import json
from pathlib import Path
import sys

import pytest


PACKAGE_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PACKAGE_ROOT))

from livox_ros2_driver_bringup.config_validation import (  # noqa: E402
    ConfigValidationError,
    parse_boolean,
    validate_config,
    validate_publish_frequency,
)


def _valid_config(model: str = "horizon") -> dict:
    return {
        "lidar_config": [{
            "broadcast_code": "TESTCODE0000000",
            "enable_connect": True,
            "enable_fan": True,
            "return_mode": 0,
            "coordinate": 0,
            "imu_rate": 1,
            "extrinsic_parameter_source": 0,
        }],
        "timesync_config": {
            "enable_timesync": False,
            "device_name": "/dev/ttyUSB0",
            "comm_device_type": 0,
            "baudrate_index": 2,
            "parity_index": 0,
        },
    }


def _write(tmp_path: Path, document: object) -> Path:
    path = tmp_path / "config.json"
    path.write_text(json.dumps(document), encoding="utf-8")
    return path


def test_packaged_discovery_configs_are_valid_only_when_allowed():
    for model in ("horizon", "avia"):
        path = PACKAGE_ROOT / "config" / f"{model}.json"
        result = validate_config(path, model=model, allow_auto_discovery=True)
        assert result.enabled_lidar_count == 0
        with pytest.raises(ConfigValidationError, match="no enabled Livox"):
            validate_config(path, model=model, allow_auto_discovery=False)


def test_valid_whitelist_passes_without_discovery(tmp_path):
    result = validate_config(
        _write(tmp_path, _valid_config()),
        model="horizon",
        allow_auto_discovery=False,
    )
    assert result.enabled_lidar_count == 1


@pytest.mark.parametrize("value", ["true", "1", "YES", "on"])
def test_parse_boolean_accepts_true_values(value):
    assert parse_boolean(value) is True


@pytest.mark.parametrize("value", ["false", "0", "NO", "off"])
def test_parse_boolean_accepts_false_values(value):
    assert parse_boolean(value) is False


@pytest.mark.parametrize("value", ["nan", "inf", "-inf", "0", "100.1"])
def test_publish_frequency_rejects_non_finite_or_out_of_range_values(value):
    with pytest.raises(ConfigValidationError, match="publish_freq"):
        validate_publish_frequency(value)


def test_publish_frequency_accepts_driver_range():
    assert validate_publish_frequency("0.1") == 0.1
    assert validate_publish_frequency("12.5") == 12.5
    assert validate_publish_frequency("100") == 100.0


def test_missing_or_malformed_file_fails_closed(tmp_path):
    with pytest.raises(ConfigValidationError, match="does not exist"):
        validate_config(
            tmp_path / "missing.json",
            model="avia",
            allow_auto_discovery=True,
        )

    malformed = tmp_path / "malformed.json"
    malformed.write_text("{", encoding="utf-8")
    with pytest.raises(ConfigValidationError, match="not readable UTF-8 JSON"):
        validate_config(
            malformed,
            model="avia",
            allow_auto_discovery=True,
        )


def test_invalid_or_duplicate_broadcast_code_fails_closed(tmp_path):
    config = _valid_config()
    config["lidar_config"][0]["broadcast_code"] = "TOO-LONG-OR-BAD"
    with pytest.raises(ConfigValidationError, match="exactly 15 ASCII"):
        validate_config(
            _write(tmp_path, config),
            model="horizon",
            allow_auto_discovery=False,
        )

    config = _valid_config()
    config["lidar_config"].append(dict(config["lidar_config"][0]))
    with pytest.raises(ConfigValidationError, match="duplicate broadcast code"):
        validate_config(
            _write(tmp_path, config),
            model="horizon",
            allow_auto_discovery=False,
        )


def test_model_specific_return_mode_is_enforced(tmp_path):
    config = _valid_config()
    config["lidar_config"][0]["return_mode"] = 3
    with pytest.raises(ConfigValidationError, match="for horizon"):
        validate_config(
            _write(tmp_path, config),
            model="horizon",
            allow_auto_discovery=False,
        )
    assert validate_config(
        _write(tmp_path, config),
        model="avia",
        allow_auto_discovery=False,
    ).enabled_lidar_count == 1


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("comm_device_type", 1, "must be 0"),
        ("baudrate_index", 19, "between 0 and 18"),
        ("parity_index", 4, "between 0 and 3"),
    ],
)
def test_timesync_indexes_are_bounded(tmp_path, field, value, message):
    config = _valid_config()
    config["timesync_config"][field] = value
    with pytest.raises(ConfigValidationError, match=message):
        validate_config(
            _write(tmp_path, config),
            model="horizon",
            allow_auto_discovery=False,
        )


def test_driver_buffer_and_device_count_limits_are_enforced(tmp_path):
    config = _valid_config()
    config["timesync_config"]["device_name"] = "/" + "x" * 255
    with pytest.raises(ConfigValidationError, match="255-byte"):
        validate_config(
            _write(tmp_path, config),
            model="horizon",
            allow_auto_discovery=False,
        )

    config = _valid_config()
    entry = config["lidar_config"][0]
    config["lidar_config"] = [
        {**entry, "broadcast_code": f"TESTCODE{i:07d}"}
        for i in range(33)
    ]
    with pytest.raises(ConfigValidationError, match="32-device"):
        validate_config(
            _write(tmp_path, config),
            model="horizon",
            allow_auto_discovery=False,
        )
