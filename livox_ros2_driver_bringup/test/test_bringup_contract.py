import ast
import json
from pathlib import Path
import xml.etree.ElementTree as ET


PACKAGE_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = PACKAGE_ROOT.parent
COMMON_FIXED_PARAMETERS = {
    "multi_topic": 0,
    "data_src": 0,
    "output_data_type": 0,
    "cmdline_input_bd_code": "",
    "lvx_file_path": "",
}
FIXED_PARAMETER_NAMES = {"xfer_format", *COMMON_FIXED_PARAMETERS}
LAUNCH_ARGUMENTS = {
    "user_config_path",
    "publish_freq",
    "frame_id",
    "allow_auto_discovery",
}


def _launch_source(name: str) -> str:
    return (PACKAGE_ROOT / "launch" / f"{name}.launch.py").read_text()


def _driver_source(name: str) -> str:
    return (
        REPO_ROOT / "livox_ros2_driver" / "livox_ros2_driver" / name
    ).read_text()


def _literal_assignments(source: str) -> dict[str, object]:
    tree = ast.parse(source)
    values = {}
    for node in ast.walk(tree):
        if not isinstance(node, ast.Dict):
            continue
        for key, value in zip(node.keys, node.values):
            if isinstance(key, ast.Constant) and key.value in FIXED_PARAMETER_NAMES:
                try:
                    values[key.value] = ast.literal_eval(value)
                except (ValueError, TypeError):
                    pass
    return values


def _declared_launch_arguments(source: str) -> set[str]:
    tree = ast.parse(source)
    arguments = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        if not isinstance(node.func, ast.Name):
            continue
        if node.func.id != "DeclareLaunchArgument" or not node.args:
            continue
        if isinstance(node.args[0], ast.Constant):
            arguments.add(node.args[0].value)
    return arguments


def test_horizon_default_config_is_empty_and_safe():
    config = json.loads((PACKAGE_ROOT / "config" / "horizon.json").read_text())
    assert config["lidar_config"] == []
    assert config["timesync_config"]["enable_timesync"] is False


def test_avia_default_config_is_disabled_zero_placeholder():
    config = json.loads((PACKAGE_ROOT / "config" / "avia.json").read_text())
    assert len(config["lidar_config"]) == 1
    lidar = config["lidar_config"][0]
    assert lidar["broadcast_code"] == "0" * 15
    assert lidar["enable_connect"] is False
    assert config["timesync_config"]["enable_timesync"] is False


def test_custommsg_launches_keep_xfer_format_one():
    for model in ("horizon", "avia"):
        source = _launch_source(model)
        assert _literal_assignments(source)["xfer_format"] == 1


def test_pointcloud2_launches_use_xfer_format_zero():
    for model in ("horizon", "avia"):
        source = _launch_source(f"{model}_pointcloud2")
        assert _literal_assignments(source)["xfer_format"] == 0


def test_each_model_keeps_node_name_across_message_formats():
    for model in ("horizon", "avia"):
        expected_node_name = f'livox_{model}_publisher'
        for name in (model, f"{model}_pointcloud2"):
            assert f'name="{expected_node_name}"' in _launch_source(name)


def test_all_launches_keep_driver_and_argument_contract():
    for model in ("horizon", "avia"):
        for name in (model, f"{model}_pointcloud2"):
            source = _launch_source(name)
            assignments = _literal_assignments(source)
            assert {
                key: assignments[key] for key in COMMON_FIXED_PARAMETERS
            } == COMMON_FIXED_PARAMETERS
            assert _declared_launch_arguments(source) == LAUNCH_ARGUMENTS
            assert "OpaqueFunction(" in source
            assert 'package="livox_ros2_driver"' in source
            assert 'executable="livox_ros2_driver_node"' in source


def test_cmake_installs_all_four_launch_files():
    source = (PACKAGE_ROOT / "CMakeLists.txt").read_text()
    for name in (
        "horizon.launch.py",
        "avia.launch.py",
        "horizon_pointcloud2.launch.py",
        "avia_pointcloud2.launch.py",
    ):
        assert f"launch/{name}" in source


def test_vendor_is_pinned_to_immutable_commit():
    source = (REPO_ROOT / "livox_sdk_vendor" / "CMakeLists.txt").read_text()
    assert 'set(livox_sdk_REV "14c533dd7175bd90a6b568c0aa1733f35d36cb89")' in source
    assert 'set(livox_sdk_REV "v2.3.1")' not in source


def test_driver_uses_rclcpp_signal_lifecycle_and_wakes_blocked_polling():
    driver = _driver_source("livox_ros2_driver.cpp")
    lddc_header = _driver_source("lddc.h")
    lddc = _driver_source("lddc.cpp")

    assert "#include <csignal>" not in driver
    assert "SignalHandler" not in driver
    assert "signal(SIGINT" not in driver
    assert "exit(signum)" not in driver
    assert "void RequestExit(void);" in lddc_header
    assert "lddc_ptr_->RequestExit();" in driver
    assert "poll_thread_->joinable()" in driver
    assert "Lds *const lds = lds_;" in lddc
    assert "lds->RequestExit();" in lddc
    assert "lds->semaphore_.Signal();" in lddc
    assert (
        "while (!QueueIsEmpty(p_queue) && !lds_->IsRequestExit())"
        in lddc
    )
    assert lddc.count("if (lds_->IsRequestExit())") >= 3


def test_imu_packets_wake_distribution_without_accumulating_tokens():
    lds_header = _driver_source("lds.h")
    lds = _driver_source("lds.cpp")

    assert "void SignalIfIdle()" in lds_header
    assert lds.count("semaphore_.SignalIfIdle();") >= 2


def test_imu_output_uses_ros_units_and_marks_orientation_unavailable():
    lddc = _driver_source("lddc.cpp")

    assert "kStandardGravity = 9.80665" in lddc
    assert "imu_data.header.frame_id = frame_id_;" in lddc
    assert "imu_data.orientation_covariance[0] = -1.0;" in lddc
    for axis in ("x", "y", "z"):
        assert (
            f"imu_data.linear_acceleration.{axis} = "
            f"imu->acc_{axis} * kStandardGravity;"
        ) in lddc


def test_all_packages_are_versioned_for_v1_beta():
    for package_xml in REPO_ROOT.glob("*/package.xml"):
        root = ET.parse(package_xml).getroot()
        assert root.findtext("version") == "1.0.0"

    version_header = _driver_source("include/livox_ros2_driver.h")
    assert "#define LIVOX_ROS_DRIVER_VER_MAJOR 1" in version_header
    assert "#define LIVOX_ROS_DRIVER_VER_MINOR 0" in version_header
    assert "#define LIVOX_ROS_DRIVER_VER_PATCH 0" in version_header


def test_rdk_scripts_use_the_merged_workspace_and_explicit_message_modes():
    build = (REPO_ROOT / "rdk" / "build.sh").read_text()
    start = (REPO_ROOT / "rdk" / "start_driver.sh").read_text()
    validate = (REPO_ROOT / "rdk" / "validate_topics.sh").read_text()

    assert "livox_unified_bringup" not in build
    assert "livox_ros2_driver_source" not in build
    assert "livox_ros2_driver_bringup" in build
    assert "merge-base --is-ancestor v0.0.1 HEAD" in build
    assert "cmp" in build
    assert "horizon_pointcloud2.launch.py" in build

    assert "horizon|avia [custommsg|pointcloud2]" in start
    assert 'launch_file="${model}_pointcloud2.launch.py"' in start
    assert 'launch_file="$model.launch.py"' in start
    assert "allow_auto_discovery:=false" in start
    assert "site_config" in start

    assert "livox_interfaces/msg/CustomMsg" in validate
    assert "sensor_msgs/msg/PointCloud2" in validate
    assert "sensor_msgs/msg/Imu" in validate


def test_rdk_network_profile_cannot_take_the_default_or_management_route():
    source = (REPO_ROOT / "rdk" / "install_eth1_networkmanager.sh").read_text()

    assert 'address="${LIVOX_HOST_ADDRESS:-}"' in source
    assert "192.168.1.50" not in source
    assert "sudo --preserve-env=PATH" not in source
    assert "PATH=/usr/sbin:/usr/bin:/sbin:/bin" in source
    assert "ipv4.never-default yes" in source
    assert 'ipv4.gateway ""' in source
    assert 'ipv4.dns ""' in source
    assert "ipv6.method disabled" in source
    assert "99-livox-management-route.yaml" in source
    assert "ip route replace" in source
    assert "eth1 意外获得默认路由" in source
    assert "管理路由" in source
