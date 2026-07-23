import ast
import json
from pathlib import Path


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
