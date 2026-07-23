# Livox Horizon 接入、参数与启动

## 1. 接线与网络

1. 断电状态下固定雷达并连接线束，确认极性后再上电。
2. Horizon 本体使用 10–15 V DC，推荐 12 V；普通以太网口不提供 PoE。
3. 雷达和运行驱动的有线网卡必须位于同一 IPv4 子网。
4. 出厂地址通常为 `192.168.1.1XX/24`，其中 `XX` 是序列号末两位；主机可使用
   不冲突的地址，例如 `192.168.1.50/24`。
5. 用 Livox Viewer 确认实际 IP、固件和完整 15 位 Broadcast Code。设备若已改
   为 DHCP 或自定义静态地址，以 Viewer 的现场值为准。

主机临时网卡配置示例：

```bash
sudo ip addr add 192.168.1.50/24 dev enp3s0
sudo ip link set enp3s0 up
ip addr show dev enp3s0
```

将 `enp3s0` 和地址替换为现场值。不要盲目关闭整机防火墙；只放行 Livox 发现和
数据所需的有线网卡流量。

## 2. 首次自动发现

默认 `livox_ros2_driver_bringup/config/horizon.json` 使用：

```json
{
  "lidar_config": []
}
```

同时 launch 将 `cmdline_input_bd_code` 设为空，因此第一次联调会自动发现同网段
受支持的第一代 Livox。共享网段可能发现非目标设备，只应把该模式用于首次排障。

## 3. 生产白名单

从 Livox Viewer 读取真实 15 位码后，在仓库根目录执行：

```bash
python3 scripts/configure_broadcast.py horizon 0ABCDEFGHIJKLMN
```

脚本默认生成 `site_config/horizon.json`（已被 Git 忽略），关键字段为：

```json
{
  "broadcast_code": "真实15位码",
  "enable_connect": true,
  "enable_fan": true,
  "return_mode": 0,
  "coordinate": 0,
  "imu_rate": 1,
  "extrinsic_parameter_source": 0
}
```

不要提交真实 Broadcast Code、设备序列号或现场 IP。推荐使用
`--output /etc/livox/horizon.json` 生成仓库外配置。

## 4. Horizon 字段选择

| 字段 | 推荐基线 | 可选值与限制 |
|---|---:|---|
| `return_mode` | `0` | `0` 首回波，`1` 最强回波，`2` 双回波；Horizon 不使用 `3` |
| `coordinate` | `0` | `0` 笛卡尔坐标；LIO 不应改为 `1` 球坐标 |
| `imu_rate` | `1` | `0` 关闭，`1` 为 200 Hz；旧固件或无 IMU 需求时先用 `0` |
| `extrinsic_parameter_source` | `0` | `0` 不自动补偿；只有已在 Viewer 完成外参流程时才评估 `1` |
| `enable_fan` | `true` | 保持官方默认散热策略 |

为保持上游驱动完整兼容性，Horizon 建议使用官方支持矩阵要求的
`06.07.0000` 或更新固件。协议层的回波和 IMU 命令从 `06.04.0000` 起可用，
GPS 时间同步另要求至少 `06.06.0000`；不要把单条命令门槛误当成整个驱动的降级
兼容承诺。

改变回波模式会改变点数和带宽，必须重新验证网络丢包、话题频率与下游算法。

## 5. 构建后启动

Horizon 提供两个入口，配置校验、节点名 `livox_horizon_publisher` 和四个公开参数
完全相同，区别仅是固定的点云格式：

```bash
source /opt/ros/humble/setup.bash
source ~/ws_livox/install/setup.bash

# CustomMsg：xfer_format=1
ros2 launch livox_ros2_driver_bringup horizon.launch.py

# PointCloud2：xfer_format=0
ros2 launch livox_ros2_driver_bringup horizon_pointcloud2.launch.py
```

使用白名单；下例假设在仓库根目录启动，并保持上游点云与 IMU 共同兼容的默认
frame。按下游所需格式选择其中一个入口，不要同时运行：

```bash
# CustomMsg
ros2 launch livox_ros2_driver_bringup horizon.launch.py \
  user_config_path:="$(pwd)/site_config/horizon.json" \
  publish_freq:=10.0 \
  frame_id:=livox_frame

# PointCloud2
ros2 launch livox_ros2_driver_bringup horizon_pointcloud2.launch.py \
  user_config_path:="$(pwd)/site_config/horizon.json" \
  publish_freq:=10.0 \
  frame_id:=livox_frame
```

若配置写在 `/etc/livox/horizon.json`，将路径替换为该绝对路径。launch 会在节点
启动前验证文件和白名单；路径拼错、JSON 损坏、Horizon 不支持的 `return_mode=3`
或无启用设备都会直接失败。仅当外部空配置确实用于首次联调时，才显式追加
`allow_auto_discovery:=true`。

`frame_id` 同时修改点云与 IMU 消息头；默认均为 `livox_frame`。该参数不执行
LiDAR、内置 IMU 与机体之间的外参变换。

显示可覆盖参数：

```bash
ros2 launch livox_ros2_driver_bringup horizon.launch.py --show-args
ros2 launch livox_ros2_driver_bringup horizon_pointcloud2.launch.py --show-args
```

两者都只公开 `user_config_path`、`publish_freq`、`frame_id` 和
`allow_auto_discovery`。本版本不允许 `xfer_format=2`。

## 6. 实机检查

```bash
ros2 node list
ros2 topic type /livox/lidar
ros2 topic type /livox/imu
ros2 topic info -v /livox/lidar
ros2 topic hz /livox/lidar
ros2 topic hz /livox/imu
```

应看到节点 `livox_horizon_publisher`。`horizon.launch.py` 的点云为
`livox_interfaces/msg/CustomMsg`；`horizon_pointcloud2.launch.py` 的点云为
`sensor_msgs/msg/PointCloud2`，字段布局为 Livox PointXYZRTL：
`x`、`y`、`z`、`intensity` 是 `float32`，`tag`、`line` 是 `uint8`。两个入口
的 IMU 都是 `sensor_msgs/msg/Imu`。

Horizon 对无目标或超量程位置会输出 `(0,0,0)`，驱动也用零点保持丢包处的时间
结构；避障和 LIO 前端必须显式过滤零坐标。PointCloud2 没有逐点时间，建议用于
避障/可视化；LIO 使用 CustomMsg 的 `timebase + offset_time`。IMU 线加速度已
转换为 `m/s²`，不可用姿态以 `orientation_covariance[0] = -1` 标记。

默认 `timesync=false` 时 Header 使用设备上电后的相对时间，雷达和内置 IMU 同基
但不等于主机墙钟；动态 TF 或外部传感器融合必须另行完成时间同步。

启动 PointCloud2 入口后执行实机消息验收：

```bash
./scripts/validate_topics.sh \
  --topic /livox/lidar \
  --expected-type sensor_msgs/msg/PointCloud2
```

CustomMsg 与 PointCloud2 使用同一个 `/livox/lidar`，不能在同一 ROS domain 中
同时运行；需要隔离时使用不同 `ROS_DOMAIN_ID`。无硬件 smoke 只能检查
`xfer_format=0` 和节点存活。publisher 收到设备数据后才惰性创建，因而无硬件
环境不能用 `ros2 topic type` 证明 PointCloud2 类型。

## 7. 常见问题

- **Viewer 和驱动都找不到设备**：检查供电、链路灯、网卡地址/掩码、路由和
  UDP 防火墙。
- **Viewer 能看到，驱动不连接**：恢复自动发现验证，再逐字符检查 15 位白名单。
- **有点云无 IMU**：检查固件、`imu_rate`、设备状态及是否误连其他雷达。
- **话题存在但下游收不到**：核对 `ROS_DOMAIN_ID`、RMW、类型和 QoS。
- **启用时间同步后失败**：先阅读 [PARAMETERS.md](PARAMETERS.md)；JSON 串口项
  不等于自动支持 PTP，也不替代 PPS/NMEA 硬件接线。
