# 公共参数、JSON 字段与话题契约

## Launch 参数

Horizon 与 Avia 的启动文件都固定以下驱动参数：

| 参数 | 固定值 | 含义 |
|---|---:|---|
| `xfer_format` | `1` | 发布 `livox_interfaces/msg/CustomMsg` |
| `multi_topic` | `0` | 单机使用共享 `/livox/lidar` 与 `/livox/imu` |
| `data_src` | `0` | 直接连接实体 LiDAR，不读取 Hub/LVX |
| `output_data_type` | `0` | 输出到 ROS |
| `cmdline_input_bd_code` | 空字符串 | 不使用上游假默认广播码 |
| `lvx_file_path` | 空字符串 | 不读取 LVX 文件 |

可从命令行覆盖：

| 参数 | 默认值 | 说明 |
|---|---|---|
| `user_config_path` | 对应型号的安装后 JSON | 推荐生产环境传入仓库外绝对路径 |
| `publish_freq` | `10.0` | 有限浮点 Hz；bringup 在启动前要求 0.1–100 Hz |
| `frame_id` | `livox_frame` | 仅设置点云消息 frame；见下方限制 |
| `allow_auto_discovery` | `false` | 只允许合法外部空白名单进入自动发现；随包首次联调配置自动获准 |

固定的官方驱动基线在 `lddc.cpp` 中把 IMU 消息的 `header.frame_id` 硬编码为
`livox_frame`，所以覆盖 launch 的 `frame_id` 不会改变 IMU。为避免 LIO 收到
不一致的点云/IMU frame，推荐保持默认 `livox_frame`；若下游确实需要其他坐标系，
应由 TF 或消息重映射/转换层统一处理，而不是误以为该参数会同时修改两类消息。

## 启动前配置门禁

固定上游驱动会忽略 `ParseConfigFile()` 失败，并在白名单为空时转入自动连接。统一
bringup 因此在创建驱动节点前执行 fail-closed 校验：

- 文件必须存在、可读且是 UTF-8 JSON；
- `lidar_config` 和 `timesync_config` 类型必须正确；
- 每个 Broadcast Code 必须是恰好 15 位 ASCII 字母或数字且不得重复；
- 回波模式、坐标、IMU 和外参字段必须在对应型号的范围内；
- 外部生产配置必须至少包含一个 `enable_connect=true` 条目。

随包 `horizon.json` / `avia.json` 是明确用于首次联调的自动发现模板。其他空白名单
必须显式传 `allow_auto_discovery:=true`；该开关不会放过缺失或损坏的配置文件。

`xfer_format=0` 可发布带 Livox 扩展字段的 PointCloud2；本项目为 LIO 固定使用
`1`。上游说明中的 `xfer_format=2` 尚未受支持，不应启用。

## JSON 的 `lidar_config`

| 字段 | 类型 | 说明 |
|---|---|---|
| `broadcast_code` | string | Viewer 显示的完整 15 位码 |
| `enable_connect` | bool | `true` 加入连接白名单；`false` 不连接该条目 |
| `enable_fan` | bool | 风扇控制 |
| `return_mode` | int | 0 首回波、1 最强、2 双回波；3 三回波仅 Avia |
| `coordinate` | int | 0 笛卡尔、1 球坐标 |
| `imu_rate` | int | 0 关闭、1 为 200 Hz；其他值未定义 |
| `extrinsic_parameter_source` | int | 0 不自动补偿、1 使用设备外参 |

生产配置应至少包含一个 `enable_connect=true` 的真实设备。生成脚本默认写到
被 Git 忽略的 `site_config/`；默认自动发现只用于首次联调。

## `timesync_config`

默认保持：

```json
{
  "enable_timesync": false,
  "device_name": "/dev/ttyUSB0",
  "comm_device_type": 0,
  "baudrate_index": 2,
  "parity_index": 0
}
```

该功能只用于官方旧驱动的 GPS NMEA 串口 + LiDAR PPS 时间同步：

- `comm_device_type=0`：串口或 USB 虚拟串口；
- `baudrate_index=2`：9600 baud；
- `parity_index=0`：8N1；
- GPS 需向主机提供 1 Hz GPRMC/GNRMC，并把 PPS 接入雷达同步端。

它不是 GNSS 定位驱动，不发布经纬度，不自动完成外参，也不是 PTP。未完成真实
串口、PPS、固件和时间戳验证时，不要把 `enable_timesync` 改为 `true`。

## 话题

在 `multi_topic=0`、`xfer_format=1` 下：

| 话题 | 类型 |
|---|---|
| `/livox/lidar` | `livox_interfaces/msg/CustomMsg` |
| `/livox/imu` | `sensor_msgs/msg/Imu` |

若下游看不到数据，按顺序检查：

1. 驱动是否连接了正确设备；
2. `ROS_DOMAIN_ID` 与 `RMW_IMPLEMENTATION` 是否一致；
3. `ros2 topic info -v` 中类型和 QoS 是否兼容；
4. 主机网卡、路由和 UDP 防火墙；
5. 白名单是否为真实 15 位 Broadcast Code。
