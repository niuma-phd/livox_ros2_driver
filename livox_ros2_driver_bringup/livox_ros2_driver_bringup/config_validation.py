"""Fail-closed validation for first-generation Livox JSON configurations."""

from dataclasses import dataclass
import json
import math
from pathlib import Path
import re


_BROADCAST_CODE = re.compile(r"[A-Za-z0-9]{15}", re.ASCII)
_RETURN_MODES = {
    "horizon": {0, 1, 2},
    "avia": {0, 1, 2, 3},
}


class ConfigValidationError(ValueError):
    """Raised when a Livox configuration must not be passed to the driver."""


@dataclass(frozen=True)
class ValidationResult:
    """Validated path and connection intent used by the launch layer."""

    path: Path
    enabled_lidar_count: int


def parse_boolean(value: str) -> bool:
    """Parse a ROS launch-style boolean value."""
    normalized = value.strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    raise ConfigValidationError(
        "allow_auto_discovery must be one of true/false, 1/0, yes/no, or on/off"
    )


def validate_publish_frequency(value: str) -> float:
    """Return a finite driver-supported point-cloud publish frequency."""
    try:
        frequency = float(value)
    except ValueError as exc:
        raise ConfigValidationError(
            f"publish_freq could not convert string to float: {value!r}"
        ) from exc
    if not math.isfinite(frequency):
        raise ConfigValidationError("publish_freq must be finite")
    if not 0.1 <= frequency <= 100.0:
        raise ConfigValidationError("publish_freq must be between 0.1 and 100 Hz")
    return frequency


def _require_type(mapping: dict, key: str, expected_type: type, context: str):
    if key not in mapping:
        raise ConfigValidationError(f"{context}.{key} is required")
    value = mapping[key]
    if expected_type is int:
        valid = isinstance(value, int) and not isinstance(value, bool)
    else:
        valid = isinstance(value, expected_type)
    if not valid:
        raise ConfigValidationError(
            f"{context}.{key} must be {expected_type.__name__}"
        )
    return value


def _validate_timesync(config: object) -> None:
    if not isinstance(config, dict):
        raise ConfigValidationError("timesync_config must be an object")

    _require_type(config, "enable_timesync", bool, "timesync_config")
    device_name = _require_type(config, "device_name", str, "timesync_config")
    comm_type = _require_type(config, "comm_device_type", int, "timesync_config")
    baudrate = _require_type(config, "baudrate_index", int, "timesync_config")
    parity = _require_type(config, "parity_index", int, "timesync_config")

    if not device_name:
        raise ConfigValidationError("timesync_config.device_name must not be empty")
    if "\0" in device_name or len(device_name.encode("utf-8")) > 255:
        raise ConfigValidationError(
            "timesync_config.device_name must fit the driver's 255-byte path buffer"
        )
    if comm_type != 0:
        raise ConfigValidationError(
            "timesync_config.comm_device_type must be 0 (UART)"
        )
    if baudrate not in range(19):
        raise ConfigValidationError(
            "timesync_config.baudrate_index must be between 0 and 18"
        )
    if parity not in range(4):
        raise ConfigValidationError(
            "timesync_config.parity_index must be between 0 and 3"
        )


def _validate_lidar_entry(entry: object, index: int, model: str) -> bool:
    context = f"lidar_config[{index}]"
    if not isinstance(entry, dict):
        raise ConfigValidationError(f"{context} must be an object")

    code = _require_type(entry, "broadcast_code", str, context)
    if _BROADCAST_CODE.fullmatch(code) is None:
        raise ConfigValidationError(
            f"{context}.broadcast_code must be exactly 15 ASCII alphanumeric characters"
        )

    enabled = _require_type(entry, "enable_connect", bool, context)
    _require_type(entry, "enable_fan", bool, context)
    return_mode = _require_type(entry, "return_mode", int, context)
    coordinate = _require_type(entry, "coordinate", int, context)
    imu_rate = _require_type(entry, "imu_rate", int, context)
    extrinsic_source = _require_type(
        entry, "extrinsic_parameter_source", int, context
    )

    if return_mode not in _RETURN_MODES[model]:
        allowed = ", ".join(str(value) for value in sorted(_RETURN_MODES[model]))
        raise ConfigValidationError(
            f"{context}.return_mode must be one of {allowed} for {model}"
        )
    if coordinate not in {0, 1}:
        raise ConfigValidationError(f"{context}.coordinate must be 0 or 1")
    if imu_rate not in {0, 1}:
        raise ConfigValidationError(f"{context}.imu_rate must be 0 or 1")
    if extrinsic_source not in {0, 1}:
        raise ConfigValidationError(
            f"{context}.extrinsic_parameter_source must be 0 or 1"
        )
    if "enable_high_sensitivity" in entry:
        _require_type(entry, "enable_high_sensitivity", bool, context)

    return enabled


def validate_config(
    path: str | Path,
    *,
    model: str,
    allow_auto_discovery: bool,
) -> ValidationResult:
    """Validate a config before the upstream driver can silently fall back."""
    if model not in _RETURN_MODES:
        raise ConfigValidationError("model must be 'horizon' or 'avia'")

    candidate = Path(path).expanduser()
    try:
        resolved = candidate.resolve(strict=True)
    except (FileNotFoundError, OSError) as exc:
        raise ConfigValidationError(
            f"configuration file does not exist or is inaccessible: {candidate}"
        ) from exc
    if not resolved.is_file():
        raise ConfigValidationError(f"configuration path is not a file: {resolved}")

    try:
        document = json.loads(resolved.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ConfigValidationError(
            f"configuration file is not readable UTF-8 JSON: {resolved}: {exc}"
        ) from exc
    if not isinstance(document, dict):
        raise ConfigValidationError("configuration root must be an object")

    lidar_config = document.get("lidar_config")
    if not isinstance(lidar_config, list):
        raise ConfigValidationError("lidar_config must be an array")
    if len(lidar_config) > 32:
        raise ConfigValidationError(
            "lidar_config exceeds the driver's 32-device limit"
        )

    enabled_count = 0
    seen_codes = set()
    for index, entry in enumerate(lidar_config):
        enabled_count += int(_validate_lidar_entry(entry, index, model))
        code = entry["broadcast_code"]
        if code in seen_codes:
            raise ConfigValidationError(
                f"lidar_config contains duplicate broadcast code: {code}"
            )
        seen_codes.add(code)

    _validate_timesync(document.get("timesync_config"))

    if enabled_count == 0 and not allow_auto_discovery:
        raise ConfigValidationError(
            "configuration has no enabled Livox whitelist entry; "
            "refusing the upstream driver's automatic-discovery fallback"
        )

    return ValidationResult(resolved, enabled_count)
