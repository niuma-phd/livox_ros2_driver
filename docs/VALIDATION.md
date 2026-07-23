# 构建与无硬件验证

本文件只记录可重复的验证口径。具体镜像构建文件不属于本仓库。

## 目标环境

- Ubuntu 22.04
- ROS 2 Humble
- Release 构建
- `BUILTIN_livox_sdk=ON`

## 2026-07-23 CustomMsg 入口实际验证结果

以下结果只覆盖原有 `horizon.launch.py` 和 `avia.launch.py` CustomMsg 入口，
不作为新增 PointCloud2 入口的验证证据。当时源码使用本机已有镜像
`ros2-livox-avia-driver:humble` 验证；该镜像仅作为本地测试环境，仓库中没有
Dockerfile、Compose 或镜像产物。

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

## 2026-07-23 PointCloud2 入口实际验证结果

新增入口继续使用同一本机镜像
`ros2-livox-avia-driver:humble`（镜像 ID 与上表一致）验证。源码以只读目录挂载，
构建与测试产物留在临时容器中；仓库没有加入 Dockerfile、Compose 或镜像产物。

| 项目 | 结果 |
|---|---|
| 本地测试 | 45 个 pytest 用例通过；Ruff、launch AST、JSON、shell 语法及 `git diff --check` 通过 |
| Humble 全量构建 | Release 模式完成 4 个包：interfaces、SDK vendor、driver、bringup |
| Humble bringup 测试 | 4 个 CTest 目标通过；`colcon test-result` 汇总 49 tests、0 errors、0 failures、0 skipped |
| 安装检查 | 四个 launch 文件均出现在安装树 |
| Launch 参数 | 四个 launch 的 `--show-args` 均列出相同的 4 个公开参数 |
| Horizon PointCloud2 smoke | 节点出现并持续运行；`xfer_format=0`、`publish_freq=12.5`、`frame_id=horizon_pointcloud2_frame`、配置路径正确 |
| Avia PointCloud2 smoke | 节点出现并持续运行；`xfer_format=0`、`publish_freq=12.5`、`frame_id=avia_pointcloud2_frame`、配置路径正确 |
| 驱动初始化 | 两型号日志均包含 raw lidar 数据源、SDK 初始化和 `Init lds lidar success!` |

本次无硬件 smoke 未产生 `/livox/lidar`；这符合 publisher 收到设备数据后才惰性
创建的实现，不能代替下文的实机话题类型与数据验收。

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
ros2 launch livox_ros2_driver_bringup horizon_pointcloud2.launch.py --show-args
ros2 launch livox_ros2_driver_bringup avia_pointcloud2.launch.py --show-args
```

四者都必须且只能列出：

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

timeout --signal=INT 8s \
  ros2 launch livox_ros2_driver_bringup horizon_pointcloud2.launch.py

timeout --signal=INT 8s \
  ros2 launch livox_ros2_driver_bringup avia_pointcloud2.launch.py
```

在没有雷达的环境中，预期驱动初始化 SDK、进入发现并持续运行，直到测试主动发送
SIGINT；不得出现参数解析错误、配置文件缺失、崩溃或 OOM。

对 PointCloud2 入口，无硬件 smoke 还应从节点参数确认 `xfer_format=0`，并确认
节点名仍分别为 `livox_horizon_publisher` 和 `livox_avia_publisher`。这只能证明
固定参数和节点存活。上游 publisher 会在收到设备数据后惰性创建，因此无硬件时
缺少 `/livox/lidar` 是预期现象，不能用 smoke 证明实际 topic type。

不要在同一 ROS domain 中同时运行 CustomMsg 和 PointCloud2 smoke；两者使用相同
的 `/livox/lidar`，并行执行时必须设置不同 `ROS_DOMAIN_ID`。

## 实机仍需验证

启动 PointCloud2 入口并连接对应实体雷达后执行：

```bash
./scripts/validate_topics.sh \
  --topic /livox/lidar \
  --expected-type sensor_msgs/msg/PointCloud2
```

该检查等待 `/livox/lidar`、确认类型并接收一条消息；不能用无硬件 smoke 代替。
PointCloud2 应使用 Livox PointXYZRTL 字段：`x`、`y`、`z`、`intensity` 为
`float32`，`tag`、`line` 为 `uint8`。`/livox/imu` 仍应为
`sensor_msgs/msg/Imu`。本版本禁用 `xfer_format=2`。

无硬件测试不能证明：

- Horizon / Avia 被正确发现；
- `/livox/lidar` 和 `/livox/imu` 有稳定数据；
- 频率、QoS、网络丢包和时间同步合格；
- arm64 构建或目标设备运行合格；
- LIO 外参、时间偏差或定位精度合格。
