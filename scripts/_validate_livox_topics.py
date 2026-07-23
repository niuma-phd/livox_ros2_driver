#!/usr/bin/env python3
"""Wait for a Livox ROS 2 topic, validate its type, and receive one message."""

import argparse
import shutil
import subprocess
import sys
import time


def run_ros2(*args: str, timeout: float | None = None) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["ros2", *args],
        check=False,
        capture_output=True,
        text=True,
        timeout=timeout,
    )


def wait_for_topic(topic: str, deadline: float) -> bool:
    while time.monotonic() < deadline:
        remaining = deadline - time.monotonic()
        try:
            result = run_ros2("topic", "list", timeout=min(1.0, remaining))
        except subprocess.TimeoutExpired:
            continue
        if result.returncode == 0 and topic in result.stdout.splitlines():
            return True
        time.sleep(min(0.5, max(0.0, deadline - time.monotonic())))
    return False


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--topic", default="/livox/lidar")
    parser.add_argument("--expected-type", default="livox_interfaces/msg/CustomMsg")
    parser.add_argument("--timeout", type=float, default=15.0)
    return parser.parse_args(argv)


def main(argv=None) -> int:
    args = parse_args(argv)
    if args.timeout <= 0:
        print("error: --timeout must be greater than zero", file=sys.stderr)
        return 2
    if shutil.which("ros2") is None:
        print("error: ros2 command not found; source the ROS 2 Humble environment", file=sys.stderr)
        return 2

    deadline = time.monotonic() + args.timeout
    if not wait_for_topic(args.topic, deadline):
        print(f"error: topic {args.topic!r} did not appear within {args.timeout:g}s", file=sys.stderr)
        return 1

    remaining = deadline - time.monotonic()
    if remaining <= 0:
        print(f"error: timed out while checking {args.topic!r}", file=sys.stderr)
        return 1
    try:
        type_result = run_ros2("topic", "type", args.topic, timeout=remaining)
    except subprocess.TimeoutExpired:
        print(f"error: timed out while checking {args.topic!r}", file=sys.stderr)
        return 1
    actual_type = type_result.stdout.strip()
    if type_result.returncode != 0 or actual_type != args.expected_type:
        print(
            f"error: {args.topic!r} type is {actual_type or '<unknown>'!r}, "
            f"expected {args.expected_type!r}",
            file=sys.stderr,
        )
        return 1

    try:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise subprocess.TimeoutExpired(["ros2", "topic", "echo"], args.timeout)
        echo_result = run_ros2(
            "topic", "echo", "--once", args.topic, args.expected_type,
            timeout=remaining,
        )
    except subprocess.TimeoutExpired:
        print(f"error: no message received from {args.topic!r} within {args.timeout:g}s", file=sys.stderr)
        return 1

    if echo_result.returncode != 0:
        print(echo_result.stderr.rstrip() or "error: ros2 topic echo failed", file=sys.stderr)
        return 1

    print(f"OK: received {args.expected_type} on {args.topic}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
