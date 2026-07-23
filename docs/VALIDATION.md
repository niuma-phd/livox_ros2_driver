# 构建与无硬件验证

本文件只记录可重复的验证口径。具体镜像构建文件不属于本仓库。

## 目标环境

- Ubuntu 22.04
- ROS 2 Humble
- Release 构建
- `BUILTIN_livox_sdk=ON`

## 2026-07-23 实际验证结果

最终源码使用本机已有镜像 `ros2-livox-avia-driver:humble` 验证；该镜像仅作为本地
测试环境，仓库中没有 Dockerfile、Compose 或镜像产物。

| 项目 | 结果 |
|---|---|
| 镜像 ID | `sha256:313bf6838e6059c10277e913951fd4d41e2bf8f9e7ba77dafa3b79ff245c958b` |
| 容器环境 | Ubuntu 22.04.5 LTS、ROS 2 Humble、x86_64 |
| 全量构建 | 4 个包完成：interfaces、SDK vendor、driver、bringup |
| bringup 测试 | 41 个 pytest 用例；colcon 汇总 45 tests、0 errors、0 failures |
| 安装检查 | Python validator 与 3 个脚本可发现；launch 目录无 `pyc/__pycache__` |
| Launch 参数 | Horizon / Avia 均列出 4 个参数及说明 |
| 白名单生成 | 两型号 JSON 结构正确，原子生成文件权限为 `0600` |
| Horizon smoke | 节点出现；`publish_freq=12.5`、`frame_id=horizon_frame`、配置路径正确 |
| Avia smoke | 节点出现；`publish_freq=12.5`、`frame_id=avia_frame`、配置路径正确 |
| 首次发现 | 随包 Horizon 模板启动并明确警告自动发现 |
| 失败门禁 | 缺失文件、损坏 JSON、外部空白名单、非法频率均返回 1，驱动节点未初始化 |

完整主机侧证据保存在
`/tmp/livox_ros2_driver_validation_final.6HclAw/`；终止标记为
`=== VALIDATION COMPLETE ===`。构建仍会显示固定官方核心已有的 CMake policy、
未使用全局变量和 `strncpy` 编译警告，但没有编译或链接错误。本次没有修改对应
上游 C++ 数据路径。

## 静态与单元测试

```bash
python3 -m compileall \
  livox_ros2_driver_bringup/launch \
  scripts

python3 -m pytest -q livox_ros2_driver_bringup/test
ruff check livox_ros2_driver_bringup scripts
```

## ROS 构建与测试

```bash
source /opt/ros/humble/setup.bash
cd /path/to/workspace

colcon build \
  --cmake-args \
    -DCMAKE_BUILD_TYPE=Release \
    -DBUILTIN_livox_sdk=ON

colcon test \
  --packages-select livox_ros2_driver_bringup \
  --event-handlers console_direct+
colcon test-result \
  --test-result-base build/livox_ros2_driver_bringup \
  --verbose
source install/setup.bash
```

只把新增 `livox_ros2_driver_bringup` 的契约测试作为本仓库门禁。固定官方基线自带的
全仓 lint 测试存在大量历史失败，因此不把 `colcon test` 全仓结果误写成合并代码
回归。

## Launch 参数解析

```bash
ros2 launch livox_ros2_driver_bringup horizon.launch.py --show-args
ros2 launch livox_ros2_driver_bringup avia.launch.py --show-args
```

两者都必须列出：

- `user_config_path`
- `publish_freq`
- `frame_id`
- `allow_auto_discovery`

## 无硬件启动冒烟

```bash
timeout --signal=INT 8s \
  ros2 launch livox_ros2_driver_bringup horizon.launch.py

timeout --signal=INT 8s \
  ros2 launch livox_ros2_driver_bringup avia.launch.py
```

在没有雷达的环境中，预期驱动初始化 SDK、进入发现并持续运行，直到测试主动发送
SIGINT；不得出现参数解析错误、配置文件缺失、崩溃或 OOM。

## 实机仍需验证

无硬件测试不能证明：

- Horizon / Avia 被正确发现；
- `/livox/lidar` 和 `/livox/imu` 有稳定数据；
- 频率、QoS、网络丢包和时间同步合格；
- arm64 构建或目标设备运行合格；
- LIO 外参、时间偏差或定位精度合格。
