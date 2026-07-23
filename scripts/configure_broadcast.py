#!/usr/bin/env python3
"""Generate a safe Livox Horizon or Avia JSON configuration."""

import argparse
import json
import os
from pathlib import Path
import re
import sys
import tempfile


BROADCAST_CODE_PATTERN = re.compile(r"[A-Za-z0-9]{15}", re.ASCII)


def validate_broadcast_code(code: str) -> str:
    """Return a valid Livox broadcast code or raise ValueError."""
    if BROADCAST_CODE_PATTERN.fullmatch(code) is None:
        raise ValueError("broadcast code must be exactly 15 ASCII alphanumeric characters")
    return code


def lidar_entry(code: str, *, enabled: bool) -> dict:
    """Create the driver-compatible lidar entry shared by both models."""
    return {
        "broadcast_code": code,
        "enable_connect": enabled,
        "enable_fan": True,
        "return_mode": 0,
        "coordinate": 0,
        "imu_rate": 1,
        "extrinsic_parameter_source": 0,
    }


def build_config(model: str, broadcast_code: str | None) -> dict:
    """Build model-specific safe defaults, optionally enabling one exact sensor."""
    if model not in {"horizon", "avia"}:
        raise ValueError("model must be 'horizon' or 'avia'")

    if broadcast_code is not None:
        lidar_config = [lidar_entry(validate_broadcast_code(broadcast_code), enabled=True)]
    elif model == "horizon":
        lidar_config = []
    else:
        lidar_config = [lidar_entry("0" * 15, enabled=False)]

    return {
        "lidar_config": lidar_config,
        "timesync_config": {
            "enable_timesync": False,
            "device_name": "/dev/ttyUSB0",
            "comm_device_type": 0,
            "baudrate_index": 2,
            "parity_index": 0,
        },
    }


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("model", choices=("horizon", "avia"))
    parser.add_argument("broadcast_code", help="exactly 15 ASCII letters/digits")
    parser.add_argument(
        "--output",
        help=(
            "output JSON path; defaults to "
            "the ignored site_config/<model>.json directory"
        ),
    )
    return parser.parse_args(argv)


def main(argv=None) -> int:
    args = parse_args(argv)
    try:
        config = build_config(args.model, args.broadcast_code)
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    rendered = json.dumps(config, indent=2) + "\n"
    output = (
        Path(args.output).expanduser()
        if args.output
        else Path("site_config") / f"{args.model}.json"
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    temp_path = None
    try:
        file_descriptor, temp_name = tempfile.mkstemp(
            dir=output.parent,
            prefix=f".{output.name}.",
            text=True,
        )
        temp_path = Path(temp_name)
        with os.fdopen(file_descriptor, "w", encoding="utf-8") as stream:
            stream.write(rendered)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temp_path, output)
    finally:
        if temp_path is not None:
            temp_path.unlink(missing_ok=True)

    print(f"wrote {output.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
