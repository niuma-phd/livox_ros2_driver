#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"

if (($# > 0)); then
  exec python3 "${SCRIPT_DIR}/_validate_livox_topics.py" "$@"
fi

python3 "${SCRIPT_DIR}/_validate_livox_topics.py" \
  --topic /livox/lidar \
  --expected-type livox_interfaces/msg/CustomMsg
python3 "${SCRIPT_DIR}/_validate_livox_topics.py" \
  --topic /livox/imu \
  --expected-type sensor_msgs/msg/Imu
