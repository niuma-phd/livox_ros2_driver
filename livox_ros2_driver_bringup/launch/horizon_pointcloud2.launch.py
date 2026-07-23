"""Launch Livox Horizon sensors in PointCloud2 mode with safe defaults."""

from pathlib import Path

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, OpaqueFunction
from launch.logging import get_logger
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from livox_ros2_driver_bringup.config_validation import (
    ConfigValidationError,
    parse_boolean,
    validate_config,
    validate_publish_frequency,
)

_LOGGER = get_logger("livox_ros2_driver_bringup.horizon_pointcloud2")


def _launch_horizon_pointcloud2(context, *, default_config):
    config_path = LaunchConfiguration("user_config_path").perform(context)
    try:
        explicit_discovery = parse_boolean(
            LaunchConfiguration("allow_auto_discovery").perform(context)
        )
        publish_frequency = validate_publish_frequency(
            LaunchConfiguration("publish_freq").perform(context)
        )
        packaged_default = (
            Path(config_path).resolve(strict=False)
            == Path(default_config).resolve(strict=False)
        )
        result = validate_config(
            config_path,
            model="horizon",
            allow_auto_discovery=explicit_discovery or packaged_default,
        )
    except ConfigValidationError as exc:
        raise RuntimeError(f"Horizon configuration rejected: {exc}") from exc

    if result.enabled_lidar_count == 0:
        _LOGGER.warning(
            "Horizon automatic discovery is active. Use a validated 15-character "
            "broadcast-code whitelist before sharing the sensor network."
        )

    return [Node(
        package="livox_ros2_driver",
        executable="livox_ros2_driver_node",
        name="livox_horizon_publisher",
        output="screen",
        parameters=[{
            "xfer_format": 0,
            "multi_topic": 0,
            "data_src": 0,
            "publish_freq": publish_frequency,
            "output_data_type": 0,
            "frame_id": LaunchConfiguration("frame_id"),
            "user_config_path": str(result.path),
            "cmdline_input_bd_code": "",
            "lvx_file_path": "",
        }],
    )]


def generate_launch_description():
    default_config = str(
        Path(get_package_share_directory("livox_ros2_driver_bringup"))
        / "config"
        / "horizon.json"
    )

    return LaunchDescription([
        DeclareLaunchArgument(
            "user_config_path",
            default_value=default_config,
            description="Horizon JSON configuration; use an absolute path in production.",
        ),
        DeclareLaunchArgument(
            "publish_freq",
            default_value="10.0",
            description="Point cloud publish frequency in Hz (0.1 to 100).",
        ),
        DeclareLaunchArgument(
            "frame_id",
            default_value="livox_frame",
            description="Point cloud and IMU frame.",
        ),
        DeclareLaunchArgument(
            "allow_auto_discovery",
            default_value="false",
            description=(
                "Allow a valid external config with no enabled whitelist. "
                "The packaged first-use config already enables discovery."
            ),
        ),
        OpaqueFunction(
            function=_launch_horizon_pointcloud2,
            kwargs={"default_config": default_config},
        ),
    ])
