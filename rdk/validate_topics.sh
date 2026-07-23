#!/usr/bin/env bash
set -eo pipefail

usage() {
  echo "用法: $0 custommsg|pointcloud2" >&2
  exit 2
}

[[ $# -eq 1 ]] || usage
case "$1" in
  custommsg) lidar_type="livox_interfaces/msg/CustomMsg" ;;
  pointcloud2) lidar_type="sensor_msgs/msg/PointCloud2" ;;
  *) usage ;;
esac

ROS_DISTRO="${ROS_DISTRO:-humble}"
WORKSPACE="${LIVOX_WORKSPACE:-$HOME/livox_driver}"
ros_setup="/opt/ros/$ROS_DISTRO/setup.bash"
ws_setup="$WORKSPACE/install/setup.bash"

[[ -r "$ros_setup" ]] || { echo "错误: 找不到 $ros_setup" >&2; exit 1; }
[[ -r "$ws_setup" ]] || { echo "错误: 找不到 $ws_setup" >&2; exit 1; }

# shellcheck disable=SC1090
source "$ros_setup"
# shellcheck disable=SC1090
source "$ws_setup"
set -u

"$WORKSPACE/scripts/validate_topics.sh" \
  --topic /livox/lidar \
  --expected-type "$lidar_type" \
  --timeout "${LIVOX_TOPIC_TIMEOUT:-30}"
"$WORKSPACE/scripts/validate_topics.sh" \
  --topic /livox/imu \
  --expected-type sensor_msgs/msg/Imu \
  --timeout "${LIVOX_TOPIC_TIMEOUT:-30}"
