#!/usr/bin/env bash
set -eo pipefail

usage() {
  echo "用法: $0 horizon|avia [custommsg|pointcloud2]" >&2
  exit 2
}

[[ $# -ge 1 && $# -le 2 ]] || usage
case "$1" in
  horizon|avia) model="$1" ;;
  *) usage ;;
esac
case "${2:-custommsg}" in
  custommsg)
    mode="custommsg"
    launch_file="$model.launch.py"
    message_type="livox_interfaces/msg/CustomMsg"
    ;;
  pointcloud2)
    mode="pointcloud2"
    launch_file="${model}_pointcloud2.launch.py"
    message_type="sensor_msgs/msg/PointCloud2"
    ;;
  *) usage ;;
esac

ROS_DISTRO="${ROS_DISTRO:-humble}"
WORKSPACE="${LIVOX_WORKSPACE:-$HOME/livox_driver}"
CONFIG_DIR="${LIVOX_CONFIG_DIR:-$WORKSPACE/site_config}"
config="${LIVOX_CONFIG_PATH:-$CONFIG_DIR/$model.json}"
ros_setup="/opt/ros/$ROS_DISTRO/setup.bash"
ws_setup="$WORKSPACE/install/setup.bash"

[[ -r "$ros_setup" ]] || { echo "错误: 找不到 $ros_setup" >&2; exit 1; }
[[ -r "$ws_setup" ]] ||
  { echo "错误: 找不到 $ws_setup；请先运行 ./rdk/build.sh" >&2; exit 1; }
[[ -r "$config" ]] || {
  echo "错误: 找不到 $config" >&2
  echo "请先运行: python3 scripts/configure_broadcast.py $model <15位广播码>" >&2
  exit 1
}
python3 -m json.tool "$config" >/dev/null

# shellcheck disable=SC1090
source "$ros_setup"
# shellcheck disable=SC1090
source "$ws_setup"
set -u

node_name="livox_${model}_publisher"
printf '启动 %s/%s: config=%s node=/%s lidar_type=%s\n' \
  "$model" "$mode" "$config" "$node_name" "$message_type" >&2
exec ros2 launch livox_ros2_driver_bringup "$launch_file" \
  user_config_path:="$config" \
  publish_freq:="${LIVOX_PUBLISH_FREQ:-10.0}" \
  frame_id:="${LIVOX_FRAME_ID:-livox_frame}" \
  allow_auto_discovery:=false
