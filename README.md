# livox_ros2_driver

面向 **Ubuntu 22.04 + ROS 2 Humble** 的 Livox Horizon / Avia 统一驱动仓库。

本仓库以 Livox 官方第一代 ROS 2 驱动为基线，保留官方
`livox_ros2_driver`、`livox_interfaces` 和 `livox_sdk_vendor` 三个包，
另外提供一个统一的 `livox_ros2_driver_bringup` 包，分别暴露 Horizon 与
Avia 的安全默认配置和独立启动入口。驱动数据转换核心未被改写。

## 固定来源

- 官方驱动：
  `Livox-SDK/livox_ros2_driver@1565b976ab1905f911cd2a757fc32433422b701c`
- Livox-SDK：
  `Livox-SDK/Livox-SDK@14c533dd7175bd90a6b568c0aa1733f35d36cb89`
- 合并来源：
  - `niuma-phd/ROS2_Livox_Horizon_Driver@8c5a52dfe7cf1a3db94d65af566658563854fd9d`
  - `niuma-phd/ROS2_Livox_Avia_Driver@809b9bb3cd62ddd61819f606e7675b029278057b`

详细来源和合并决策见 [docs/PROVENANCE.md](docs/PROVENANCE.md)。

## 支持范围

| 型号 | 启动文件 | 默认配置 | 默认模式 |
|---|---|---|---|
| Horizon | `horizon.launch.py` | `config/horizon.json` | 安全自动发现 |
| Avia | `avia.launch.py` | `config/avia.json` | 禁用占位条目，安全自动发现 |

两个入口默认都发布：

- `/livox/lidar`：`livox_interfaces/msg/CustomMsg`
- `/livox/imu`：`sensor_msgs/msg/Imu`

统一固定参数为 `xfer_format=1`、`multi_topic=0`、`data_src=0` 和
`output_data_type=0`，适合需要每点时间偏移与线号的 LIO 前端。

> `livox_ros_driver2` 面向 HAP / MID-360，不替代本仓库中 Horizon / Avia
> 使用的第一代 `livox_ros2_driver`。

## 原生构建

```bash
mkdir -p ~/ws_livox/src
git clone https://github.com/niuma-phd/livox_ros2_driver.git \
  ~/ws_livox/src/livox_ros2_driver

source /opt/ros/humble/setup.bash
cd ~/ws_livox

sudo apt-get update
rosdep install --from-paths src --ignore-src -r -y --rosdistro humble

colcon build --symlink-install \
  --cmake-args \
    -DCMAKE_BUILD_TYPE=Release \
    -DBUILTIN_livox_sdk=ON

source install/setup.bash
```

`BUILTIN_livox_sdk=ON` 强制使用本仓库锁定的 SDK 源码，不依赖主机上可能存在的
其他 `livox_sdk` 安装。

## 第一次连接与生产白名单

第一次排障可以直接使用随包默认配置自动发现。共享网段或生产环境必须改为真实
设备的 15 位 Broadcast Code 白名单，避免误连其他 Livox。生成脚本默认写入
已被 Git 忽略的 `site_config/`，不会把真实设备码覆盖到版本库模板。

```bash
# 在仓库根目录执行；把示例码替换为 Livox Viewer 显示的真实 15 位码
python3 scripts/configure_broadcast.py horizon 0ABCDEFGHIJKLMN
python3 scripts/configure_broadcast.py avia    0ABCDEFGHIJKLMN
```

脚本只接受恰好 15 位字母或数字，并以原子替换方式分别生成：

- `site_config/horizon.json`
- `site_config/avia.json`

启动生产白名单时必须显式传入该路径：

```bash
ros2 launch livox_ros2_driver_bringup horizon.launch.py \
  user_config_path:="$(pwd)/site_config/horizon.json"
```

也可用 `--output /absolute/path/device.json` 直接生成工作区之外的现场配置。
launch 会在启动节点前校验文件、JSON、型号字段和 Broadcast Code；外部配置路径
错误、内容损坏或没有启用项时直接失败，不会静默退回自动发现。

## 分别启动

### Horizon

```bash
source /opt/ros/humble/setup.bash
source ~/ws_livox/install/setup.bash

ros2 launch livox_ros2_driver_bringup horizon.launch.py
```

### Avia

```bash
source /opt/ros/humble/setup.bash
source ~/ws_livox/install/setup.bash

ros2 launch livox_ros2_driver_bringup avia.launch.py
```

两个入口都支持以下覆盖参数：

```bash
ros2 launch livox_ros2_driver_bringup horizon.launch.py \
  user_config_path:=/absolute/path/horizon.json \
  publish_freq:=10.0 \
  frame_id:=livox_frame
```

如确需用一份合法的外部空白名单做首次联调，还必须显式追加
`allow_auto_discovery:=true`。随包默认配置是首次联调的特例，无需该参数；缺失或
损坏的配置即使允许自动发现也会被拒绝。

上游固定基线中的 `frame_id` 只作用于点云消息；IMU 消息头仍固定为
`livox_frame`。因此需要点云与 IMU 使用同一 frame 的 LIO 部署应保持默认值，
不要只覆盖该参数。详见 [公共参数说明](docs/PARAMETERS.md)。

详细配置：

- [Horizon 接入、参数与启动](docs/HORIZON.md)
- [Avia 接入、参数与启动](docs/AVIA.md)
- [公共参数、JSON 字段与话题契约](docs/PARAMETERS.md)
- [构建及无硬件验证记录](docs/VALIDATION.md)

## 实机验收

```bash
ros2 topic type /livox/lidar
ros2 topic type /livox/imu
ros2 topic info -v /livox/lidar
ros2 topic info -v /livox/imu

./scripts/validate_topics.sh
```

预期类型分别为 `livox_interfaces/msg/CustomMsg` 和
`sensor_msgs/msg/Imu`。无实体雷达时只能验证构建、launch、参数解析和驱动
持续运行，不能证明发现、点云/IMU 频率、时间同步或 LIO 精度合格。

## 仓库边界

- 不包含 Dockerfile、Compose 文件或任何容器镜像产物。
- 不包含 rosbag、本机/现场设备 IP、真实 Broadcast Code、真实序列号或现场凭据；
  上游公开且禁用的示例配置原样保留。
- `site_config/` 已忽略，用于本机真实设备白名单。
- 不修改点云、IMU 或 SDK 数据路径；型号差异只放在 bringup、JSON 和文档层。
- 上游原始说明保存在 [docs/upstream](docs/upstream/)。
