# 构建与验证

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

## 2026-07-24 RDK Horizon 实机验证结果

以下结果覆盖 `v1.0.0 beta` 候选的数据路径提交
`d95e1954981061aea541d0344ee822e3f54b8270`。目标机为 aarch64 RDK、Ubuntu
22.04、ROS 2 Humble；使用真实 Horizon 和固定 SDK 提交
`14c533dd7175bd90a6b568c0aa1733f35d36cb89`。最终发布若只在该提交之后修订本文，
无需把文档提交误写成重新测试过的数据路径。

| 项目 | 结果 |
|---|---|
| RDK 干净构建 | Release 模式 4 个包完成；节点架构为 aarch64 |
| Python 契约测试 | 52 passed |
| bringup colcon 测试 | 4 个 CTest 目标通过；汇总 56 tests、0 errors、0 failures、0 skipped |
| SDK 日志符号隔离 | 驱动共享库动态导出的 SDK `spdlog` / `fmt::v5` 符号为 0；ROS component 仍可发现 |
| PointCloud2 | 201 帧/20 秒；到达 10.007 Hz、Header 10.000 Hz；每帧固定 24,000 点 |
| PointCloud2 ABI | `x/y/z/intensity` 为 `float32`，`tag/line` 为 `uint8`，`point_step=18`，数据长度一致 |
| CustomMsg | C++ typed probe 收到 200 帧/20 秒；到达与 Header 均为 10.000 Hz；每帧固定 24,000 点 |
| CustomMsg LIO 时间 | `header.stamp == timebase`，二者非零且严格递增；全部 480 万点的 `offset_time` 单调，帧跨度 99.819–99.856 ms |
| 点数据质量 | 两种模式均无非有限 XYZ；零 XYZ 比例约 6.7%，按 Livox 无回波语义保留 |
| PointCloud2 模式 IMU | 4,041 条/20 秒；到达 202.020 Hz、Header 202.021 Hz；最大到达间隔 7.79 ms |
| CustomMsg 模式 IMU | 4,041 条/20 秒；到达 202.014 Hz、Header 202.011 Hz；最大到达间隔 7.26 ms |
| IMU 语义 | 静止加速度模长均值约 9.756 m/s²；`orientation_covariance[0] == -1`；点云和 IMU 均为 `livox_frame` |
| 网络 | 两轮采集期间 eth0、eth1 的错误/丢弃计数及 UDP `InErrors/RcvbufErrors/SndbufErrors` 增量均为 0 |
| 路由隔离 | 采集前后，默认路由和管理链路均在 eth0；雷达路由走 eth1；`livox_lidar` NetworkManager 配置保持启用 |
| Ctrl-C 退出 | PointCloud2 5/5、CustomMsg 5/5 返回 0，均完成 SDK Deinit，无崩溃标记和残留进程 |

`rdk/validate_topics.sh` 只验证话题类型并接收一条消息，因此它是 smoke test，
不能单独证明频率或数据语义。CustomMsg 的发布频率和 LIO 时间结构使用 C++ typed
probe 验证；逐点构造 Python 对象的 rclpy 探针吞吐不足 10 Hz，只用于内容抽样，
不能据其墙钟接收率判断驱动掉帧。独立 IMU 探针用于隔离点云解析负载并检查 200 Hz
和到达间隔。

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

## 实机复测方法与未覆盖范围

启动对应入口并连接实体雷达后，分别执行：

```bash
./rdk/start_driver.sh horizon pointcloud2
./rdk/validate_topics.sh pointcloud2

./rdk/start_driver.sh horizon custommsg
./rdk/validate_topics.sh custommsg
```

两次运行不能同时占用同一设备。检查会等待 `/livox/lidar`、确认类型并接收一条
消息；完整验收还必须检查稳定频率、点数、字段或逐点时间、IMU 以及进程组 SIGINT
退出。PointCloud2 应使用 Livox PointXYZRTL 字段：`x`、`y`、`z`、`intensity`
为 `float32`，`tag`、`line` 为 `uint8`。`/livox/imu` 仍应为
`sensor_msgs/msg/Imu`。本版本禁用 `xfer_format=2`。

当前仍未覆盖：

- Avia 实机发现、数据和退出行为；当前只有公共代码路径、构建和 launch 契约证据；
- 不同 Horizon 固件、交换机或高网络负载下的丢包表现；
- PTP/GPS 同步；本次 NoSync 时间戳是设备上电后的相对时间，不能与系统 wall clock
  直接比较；
- LIO 外参、时间偏差或定位精度合格。

PointCloud2 不含逐点时间，适合当前避障用途；LIO 应使用 CustomMsg 的
`timebase + offset_time`。零 XYZ 是 Livox 无回波/超量程语义，应由下游过滤，
驱动不应静默删除并改变固定点数或时间索引。
