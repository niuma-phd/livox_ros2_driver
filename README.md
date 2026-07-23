# livox_ros2_driver

面向 **Ubuntu 22.04 + ROS 2 Humble** 的 Livox Horizon / Avia 统一驱动仓库。

本仓库以 Livox 官方第一代 ROS 2 驱动为基线，保留官方
`livox_ros2_driver`、`livox_interfaces` 和 `livox_sdk_vendor` 三个包，
另外提供一个统一的 `livox_ros2_driver_bringup` 包，分别暴露 Horizon 与
Avia 的安全默认配置和独立启动入口。v1 在固定上游基线上修正了 ROS 退出顺序、
IMU 实时分发、SI 单位和消息可用性标记，不改变两种点云消息的字段布局。

当前预发布版为
[v1.0.0-beta.1（Release 标题：v1.0.0 beta）](https://github.com/niuma-phd/livox_ros2_driver/releases/tag/v1.0.0-beta.1)，
对应提交 `76913a784a216e0a0138720179b7a7bafa6c0616`。

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

| 型号 | 点云格式 | 启动文件 | 默认配置 | 默认模式 |
|---|---|---|---|---|
| Horizon | CustomMsg | `horizon.launch.py` | `config/horizon.json` | 安全自动发现 |
| Horizon | PointCloud2 | `horizon_pointcloud2.launch.py` | `config/horizon.json` | 安全自动发现 |
| Avia | CustomMsg | `avia.launch.py` | `config/avia.json` | 禁用占位条目，安全自动发现 |
| Avia | PointCloud2 | `avia_pointcloud2.launch.py` | `config/avia.json` | 禁用占位条目，安全自动发现 |

四个入口的 `/livox/imu` 都是 `sensor_msgs/msg/Imu`。点云类型由启动文件固定：

- `horizon.launch.py` / `avia.launch.py`：
  `/livox/lidar` 为 `livox_interfaces/msg/CustomMsg`，`xfer_format=1`，用于 LIO；
- `horizon_pointcloud2.launch.py` / `avia_pointcloud2.launch.py`：
  `/livox/lidar` 为 `sensor_msgs/msg/PointCloud2`，`xfer_format=0`，用于避障和
  RViz2 可视化。

Horizon 已在 aarch64 RDK 上用实体雷达完成两种点云模式、IMU、网络隔离及退出
测试。Avia 当前只完成公共代码路径、构建和 launch 契约验证，尚未进行 Avia
实机测试。

PointCloud2 使用 Livox PointXYZRTL 布局：
`x`、`y`、`z`、`intensity` 为 `float32`，`tag`、`line` 为 `uint8`。
所有入口仍固定 `multi_topic=0`、`data_src=0` 和 `output_data_type=0`。
本版本禁用 `xfer_format=2`，不要通过其他启动方式启用。

`/livox/imu` 的角速度单位为 `rad/s`，线加速度已从 SDK 原始 `g` 转换为
ROS `sensor_msgs/Imu` 要求的 `m/s²`；雷达不提供姿态估计，因此
`orientation_covariance[0] = -1`。`frame_id` 同时作用于点云与 IMU。

Livox 会对无目标、超量程或补偿丢包的位置输出零坐标点，下游必须显式过滤
`x=y=z=0`。PointCloud2 入口没有逐点时间字段，适合避障/可视化；需要逐点时间的
LIO 应使用 CustomMsg 的 `timebase + offset_time`。

> 两种点云格式使用相同的 `/livox/lidar` 话题。不要在同一 ROS domain 中同时运行
> CustomMsg 与 PointCloud2 入口；需要并行测试时应使用不同 `ROS_DOMAIN_ID`。

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

## RDK 部署与运行

RDK 默认工作区为 `~/livox_driver`。以下示例使用 Horizon、`eth1` 雷达专网和
已发布的 beta tag；把主机地址和 Broadcast Code 替换为现场值：

```bash
git clone --branch v1.0.0-beta.1 \
  https://github.com/niuma-phd/livox_ros2_driver.git \
  ~/livox_driver
cd ~/livox_driver

LIVOX_HOST_ADDRESS=192.168.1.100/24 \
  ./rdk/install_eth1_networkmanager.sh
python3 scripts/configure_broadcast.py horizon 0ABCDEFGHIJKLMN
LIVOX_CLEAN_BUILD=1 ./rdk/build.sh
```

PointCloud2 用于避障或 RViz2。终端 1 持续运行驱动：

```bash
~/livox_driver/rdk/start_driver.sh horizon pointcloud2
```

看到雷达开始采样后，在终端 2 验收：

```bash
~/livox_driver/rdk/validate_topics.sh pointcloud2
```

CustomMsg 用于 LIO。终端 1 持续运行驱动：

```bash
~/livox_driver/rdk/start_driver.sh horizon custommsg
```

看到雷达开始采样后，在终端 2 验收：

```bash
~/livox_driver/rdk/validate_topics.sh custommsg
```

NetworkManager 脚本创建 `livox_lidar` 配置，禁止 `eth1` 提供默认路由、DNS 或
IPv6，避免影响 `eth0` 的正常网络连接。`rdk/start_driver.sh` 强制使用
`site_config/<型号>.json` 白名单，不会自动发现其他雷达。

## 分别启动

### Horizon

```bash
source /opt/ros/humble/setup.bash
source ~/ws_livox/install/setup.bash

# CustomMsg，xfer_format=1
ros2 launch livox_ros2_driver_bringup horizon.launch.py

# PointCloud2，xfer_format=0
ros2 launch livox_ros2_driver_bringup horizon_pointcloud2.launch.py
```

### Avia

```bash
source /opt/ros/humble/setup.bash
source ~/ws_livox/install/setup.bash

# CustomMsg，xfer_format=1
ros2 launch livox_ros2_driver_bringup avia.launch.py

# PointCloud2，xfer_format=0
ros2 launch livox_ros2_driver_bringup avia_pointcloud2.launch.py
```

四个入口都公开相同的 `user_config_path`、`publish_freq`、`frame_id` 和
`allow_auto_discovery` 参数。示例：

```bash
ros2 launch livox_ros2_driver_bringup horizon.launch.py \
  user_config_path:=/absolute/path/horizon.json \
  publish_freq:=10.0 \
  frame_id:=livox_frame
```

如确需用一份合法的外部空白名单做首次联调，还必须显式追加
`allow_auto_discovery:=true`。随包默认配置是首次联调的特例，无需该参数；缺失或
损坏的配置即使允许自动发现也会被拒绝。

`frame_id` 同时设置点云与 IMU 消息头；默认值为 `livox_frame`。详见
[公共参数说明](docs/PARAMETERS.md)。

详细配置：

- [Horizon 接入、参数与启动](docs/HORIZON.md)
- [Avia 接入、参数与启动](docs/AVIA.md)
- [公共参数、JSON 字段与话题契约](docs/PARAMETERS.md)
- [构建及实机验证记录](docs/VALIDATION.md)

## 实机验收

```bash
ros2 topic type /livox/lidar
ros2 topic type /livox/imu
ros2 topic info -v /livox/lidar
ros2 topic info -v /livox/imu

./scripts/validate_topics.sh

# 启动 PointCloud2 入口后
./scripts/validate_topics.sh \
  --topic /livox/lidar \
  --expected-type sensor_msgs/msg/PointCloud2
```

不传参数时，脚本按 CustomMsg 点云验收；PointCloud2 入口必须显式传入上面的
`--expected-type`。无实体雷达时只能验证构建、launch、参数解析、固定
`xfer_format` 和驱动节点持续运行。上游 publisher 会在收到设备数据后惰性创建，
因此无硬件 smoke 看不到 `/livox/lidar`，不能据此证明或否定其消息类型，也不能
证明设备发现、点云/IMU 频率、时间同步或 LIO 精度合格。

## 仓库边界

- 不包含 Dockerfile、Compose 文件或任何容器镜像产物。
- 不包含 rosbag、本机/现场设备 IP、真实 Broadcast Code、真实序列号或现场凭据；
  上游公开且禁用的示例配置原样保留。
- `site_config/` 已忽略，用于本机真实设备白名单。
- 不改变 CustomMsg 或 PointCloud2 字段布局；驱动只在 ROS 边界规范化 IMU 单位、
  frame 和不可用姿态标记，并修复分发/退出生命周期。
- 上游原始说明保存在 [docs/upstream](docs/upstream/)。
