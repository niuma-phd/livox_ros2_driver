#!/usr/bin/env bash
set -eo pipefail

ROS_DISTRO="${ROS_DISTRO:-humble}"
WORKSPACE="${LIVOX_WORKSPACE:-$HOME/livox_driver}"
ROS_SETUP="/opt/ros/$ROS_DISTRO/setup.bash"
EXPECTED_SDK_COMMIT="${LIVOX_SDK_COMMIT:-14c533dd7175bd90a6b568c0aa1733f35d36cb89}"

fail() { printf '错误: %s\n' "$*" >&2; exit 1; }

[[ -r "$ROS_SETUP" ]] ||
  fail "找不到 $ROS_SETUP；需要 Ubuntu 22.04 + ROS 2 Humble"
[[ -d "$WORKSPACE/.git" ]] || fail "$WORKSPACE 不是合并仓库的 Git checkout"
[[ -f "$WORKSPACE/livox_ros2_driver/package.xml" ]] ||
  fail "找不到 $WORKSPACE/livox_ros2_driver/package.xml"
[[ -f "$WORKSPACE/livox_ros2_driver_bringup/package.xml" ]] ||
  fail "找不到 $WORKSPACE/livox_ros2_driver_bringup/package.xml"

origin_url="$(git -C "$WORKSPACE" remote get-url origin 2>/dev/null || true)"
case "$origin_url" in
  https://github.com/niuma-phd/livox_ros2_driver|https://github.com/niuma-phd/livox_ros2_driver.git|git@github.com:niuma-phd/livox_ros2_driver.git|ssh://git@github.com/niuma-phd/livox_ros2_driver.git)
    ;;
  *) fail "origin 不是合并仓库: ${origin_url:-<未配置>}" ;;
esac

git -C "$WORKSPACE" rev-parse --verify "v0.0.1^{commit}" >/dev/null 2>&1 ||
  fail "缺少 v0.0.1 基线 tag；请先执行 git fetch --tags"
git -C "$WORKSPACE" merge-base --is-ancestor v0.0.1 HEAD ||
  fail "当前 HEAD 不包含 v0.0.1 基线"

vendor_cmake="$WORKSPACE/livox_sdk_vendor/CMakeLists.txt"
grep -Fq "$EXPECTED_SDK_COMMIT" "$vendor_cmake" ||
  fail "Livox-SDK 未固定到 $EXPECTED_SDK_COMMIT"

if [[ "${LIVOX_CLEAN_BUILD:-0}" == "1" ]]; then
  rm -rf -- "$WORKSPACE/build" "$WORKSPACE/install" "$WORKSPACE/log"
fi

# shellcheck disable=SC1090
source "$ROS_SETUP"
set -u
cd "$WORKSPACE"
colcon build \
  --merge-install \
  --packages-select \
    livox_sdk_vendor \
    livox_interfaces \
    livox_ros2_driver \
    livox_ros2_driver_bringup \
  --cmake-args \
    -DCMAKE_BUILD_TYPE=Release \
    -DBUILTIN_livox_sdk=ON

node_binary="$WORKSPACE/install/lib/livox_ros2_driver/livox_ros2_driver_node"
test -x "$node_binary" || fail "构建后缺少节点: $node_binary"

for launch in \
  horizon.launch.py \
  horizon_pointcloud2.launch.py \
  avia.launch.py \
  avia_pointcloud2.launch.py
do
  cmp \
    "$WORKSPACE/livox_ros2_driver_bringup/launch/$launch" \
    "$WORKSPACE/install/share/livox_ros2_driver_bringup/launch/$launch" ||
    fail "源码与安装区 launch 不一致: $launch"
done

file "$node_binary"
printf '构建完成: %s\n' "$WORKSPACE/install"
printf '仓库提交: %s\nSDK 提交: %s\n' \
  "$(git -C "$WORKSPACE" rev-parse HEAD)" "$EXPECTED_SDK_COMMIT"
