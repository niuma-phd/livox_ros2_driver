# Livox Avia 接入、参数与启动

## 1. 接线与网络

1. Avia 本体使用 10–15 V DC，推荐 12 V，禁止超过 15 V。
2. 若使用 Livox Converter 2.0，转换器外部输入范围是 9–30 V；不要把转换器范围
   当作雷达本体范围。
3. 雷达与主机有线网卡必须位于同一 IPv4 子网。出厂地址通常为
   `192.168.1.1XX/24`，其中 `XX` 为序列号末两位。
4. 主机可使用不冲突的地址，例如 `192.168.1.50/24`。
5. 用 Livox Viewer 核对实际 IP、固件和完整 15 位 Broadcast Code。

主机临时配置示例：

```bash
sudo ip addr add 192.168.1.50/24 dev enp3s0
sudo ip link set enp3s0 up
```

## 2. 首次自动发现

默认 `livox_ros2_driver_bringup/config/avia.json` 保留一个禁用占位条目：

```json
{
  "broadcast_code": "000000000000000",
  "enable_connect": false
}
```

launch 同时把 `cmdline_input_bd_code` 设为空。禁用条目不会形成白名单，驱动会进入
自动发现。该默认值只用于首次联调，不能把占位码改成 `enable_connect=true`。

## 3. 生产白名单

```bash
python3 scripts/configure_broadcast.py avia 0ABCDEFGHIJKLMN
```

把示例值替换为 Viewer 显示的真实 15 位码。默认生成已被 Git 忽略的
`site_config/avia.json`；也可写到仓库外：

```bash
python3 scripts/configure_broadcast.py avia 0ABCDEFGHIJKLMN \
  --output /etc/livox/avia.json
```

不要提交真实 Broadcast Code、设备序列号或现场 IP。

## 4. Avia 字段选择

| 字段 | 推荐基线 | 可选值与限制 |
|---|---:|---|
| `return_mode` | `0` | `0` 首回波，`1` 最强回波，`2` 双回波，`3` 三回波 |
| `coordinate` | `0` | `0` 笛卡尔；LIO 不使用球坐标 |
| `imu_rate` | `1` | `0` 关闭，`1` 为 200 Hz |
| `extrinsic_parameter_source` | `0` | 默认不使用设备内外参自动补偿 |
| `enable_fan` | `true` | 保持官方默认 |

Avia 的三回波 `return_mode=3` 受 Livox-SDK 协议支持，但会显著增加点数和网络吞吐。
仓库默认保持首回波，不在未验证带宽、固件和下游算法前切换到三回波。

`imu_rate=1` 和 Avia 的回波模式要求固件至少 `11.06.0000`。未知或更旧固件应先
在 Viewer 中升级；临时排障可把 `imu_rate` 设为 `0`，但使用 LIO 时必须恢复并
验证 200 Hz IMU。

## 5. 构建后启动

```bash
source /opt/ros/humble/setup.bash
source ~/ws_livox/install/setup.bash

ros2 launch livox_ros2_driver_bringup avia.launch.py
```

使用生成的白名单（下例从仓库根目录执行）：

```bash
ros2 launch livox_ros2_driver_bringup avia.launch.py \
  user_config_path:="$(pwd)/site_config/avia.json" \
  publish_freq:=10.0 \
  frame_id:=livox_frame
```

launch 会在节点启动前验证外部文件；路径缺失、JSON 损坏、非法/重复 Broadcast
Code、无启用设备或字段越界都会直接失败。只有确需外部空配置做首次联调时才追加
`allow_auto_discovery:=true`。

`frame_id` 只会修改点云消息头；固定上游驱动仍把 IMU frame 写为
`livox_frame`。LIO 需要两者一致时应保留默认值。

显示可覆盖参数：

```bash
ros2 launch livox_ros2_driver_bringup avia.launch.py --show-args
```

## 6. 实机检查

```bash
ros2 node list
ros2 topic type /livox/lidar
ros2 topic type /livox/imu
ros2 topic info -v /livox/lidar
ros2 topic hz /livox/lidar
ros2 topic hz /livox/imu
```

应看到节点 `livox_avia_publisher`，点云类型为
`livox_interfaces/msg/CustomMsg`，IMU 类型为 `sensor_msgs/msg/Imu`。

## 7. 与 LIO 联跑前

驱动话题正常只证明数据链路工作，不代表 Avia 的定位精度已经合格。至少需要：

1. 标定 LiDAR、设备内 IMU和机体之间的旋转与平移；
2. 检查点云内时间、IMU 时间与主机时间偏差；
3. 固定回波模式、发布频率和固件；
4. 用重复路线、闭环或真值数据评估 ATE/RPE 和漂移。

不要直接复用为 Horizon 标定的 LIO 外参。

## 8. 常见问题

- **找不到设备**：检查供电、同网段地址、链路和 UDP 防火墙。
- **自动发现误连其他 Livox**：立即改用真实 15 位白名单。
- **有点云无 IMU**：确认固件至少 `11.06.0000`、`imu_rate=1`，并用 Viewer
  检查设备 IMU。
- **三回波后丢包**：恢复 `return_mode=0` 基线，检查主机网卡、交换机和处理能力。
- **地图发散**：先记录原始点云/IMU并检查时间、外参和机械安装，不先修改算法。
