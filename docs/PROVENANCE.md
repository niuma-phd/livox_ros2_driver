# 来源、合并决策与仓库边界

## 来源提交

新仓库以官方历史为基础：

- `Livox-SDK/livox_ros2_driver`
  `1565b976ab1905f911cd2a757fc32433422b701c`
- `Livox-SDK/Livox-SDK`
  `14c533dd7175bd90a6b568c0aa1733f35d36cb89`

合并的两个 `niuma-phd` 部署项目：

- `ROS2_Livox_Horizon_Driver`
  `8c5a52dfe7cf1a3db94d65af566658563854fd9d`
- `ROS2_Livox_Avia_Driver`
  `809b9bb3cd62ddd61819f606e7675b029278057b`

两个来源项目都没有修改官方驱动数据路径；它们在构建时拉取同一个官方驱动提交，
区别集中在 bringup、JSON、验证脚本和型号文档。

## 合并方式

1. 保留官方三个包和 Git 历史：
   - `livox_sdk_vendor`
   - `livox_interfaces`
   - `livox_ros2_driver`
2. 增加同级 `livox_ros2_driver_bringup`，集中安装两型号的 launch 与配置。
3. 使用独立 `horizon.launch.py` / `avia.launch.py`，避免运行时猜测硬件型号。
4. 保留两来源项目已经验证的安全发现策略：
   - Horizon：空 `lidar_config`
   - Avia：禁用的 15 个零占位条目
5. 把 Livox-SDK 依赖从可移动的 `v2.3.1` 标签固定到已验证提交。
6. 在 launch 创建上游节点前校验外部 JSON，阻止配置错误静默退回自动发现。
7. v1 在同一固定核心上修正 rclcpp/SDK 退出顺序、IMU 队列唤醒、ROS SI 单位、
   IMU frame 和不可用姿态标记；不改变两种点云消息的字段布局。

## 明确拒绝的方案

- 不把 Horizon 和 Avia 各复制一份官方驱动核心；这会产生两套难以同步的代码。
- 不改用 `livox_ros_driver2`；其目标设备不是本项目的 Horizon / Avia。
- 不依靠节点自动识别型号来选择现场参数；自动发现可能连接同网段其他设备。
- 不把真实 Broadcast Code、IP、序列号或 rosbag 写入版本库。
- 真实白名单默认原子写入已忽略的 `site_config/`，不覆盖跟踪的配置模板。
- 不把 Dockerfile、Compose、entrypoint 或镜像产物合并到本仓库。

## 旧项目保护

合并工作只发生在新的本地目录：

`/home/l1u/labs/livoxx_ros2_driver`

以下现有目录保持原提交和工作树不变：

- `/home/l1u/labs/ROS2_Livox_Horizon_Driver`
- `/home/l1u/labs/ROS2_Livox_Avia_Driver`
