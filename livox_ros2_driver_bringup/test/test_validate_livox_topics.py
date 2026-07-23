import importlib.util
from pathlib import Path
from subprocess import CompletedProcess, TimeoutExpired


SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "_validate_livox_topics.py"
WRAPPER = SCRIPT.with_name("validate_topics.sh")


def _load_script():
    spec = importlib.util.spec_from_file_location("_validate_livox_topics", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_success_requires_expected_type_and_one_message(monkeypatch, capsys):
    module = _load_script()
    monkeypatch.setattr(module.shutil, "which", lambda command: "/opt/ros/humble/bin/ros2")
    monkeypatch.setattr(module, "wait_for_topic", lambda topic, deadline: True)

    calls = []

    def fake_run(*args, timeout=None):
        calls.append((args, timeout))
        if args[:2] == ("topic", "type"):
            return CompletedProcess(args, 0, "livox_interfaces/msg/CustomMsg\n", "")
        return CompletedProcess(args, 0, "header: {}\n", "")

    monkeypatch.setattr(module, "run_ros2", fake_run)
    assert module.main(["--timeout", "1"]) == 0
    assert calls[-1][0] == (
        "topic", "echo", "--once", "/livox/lidar", "livox_interfaces/msg/CustomMsg"
    )
    assert "OK:" in capsys.readouterr().out


def test_wrong_type_fails_before_echo(monkeypatch):
    module = _load_script()
    monkeypatch.setattr(module.shutil, "which", lambda command: "/opt/ros/humble/bin/ros2")
    monkeypatch.setattr(module, "wait_for_topic", lambda topic, deadline: True)
    monkeypatch.setattr(
        module,
        "run_ros2",
        lambda *args, timeout=None: CompletedProcess(args, 0, "sensor_msgs/msg/PointCloud2\n", ""),
    )
    assert module.main([]) == 1


def test_message_timeout_is_reported(monkeypatch):
    module = _load_script()
    monkeypatch.setattr(module.shutil, "which", lambda command: "/opt/ros/humble/bin/ros2")
    monkeypatch.setattr(module, "wait_for_topic", lambda topic, deadline: True)

    def fake_run(*args, timeout=None):
        if args[:2] == ("topic", "type"):
            return CompletedProcess(args, 0, "livox_interfaces/msg/CustomMsg\n", "")
        raise TimeoutExpired(args, timeout)

    monkeypatch.setattr(module, "run_ros2", fake_run)
    assert module.main(["--timeout", "0.1"]) == 1


def test_wrapper_defaults_to_lidar_and_imu_contracts():
    source = WRAPPER.read_text()
    assert "--topic /livox/lidar" in source
    assert "--expected-type livox_interfaces/msg/CustomMsg" in source
    assert "--topic /livox/imu" in source
    assert "--expected-type sensor_msgs/msg/Imu" in source


def test_topic_list_timeout_is_bounded(monkeypatch):
    module = _load_script()
    calls = []

    def fake_run(*args, timeout=None):
        calls.append(timeout)
        raise TimeoutExpired(args, timeout)

    monkeypatch.setattr(module, "run_ros2", fake_run)
    assert module.wait_for_topic("/livox/lidar", module.time.monotonic() + 0.01) is False
    assert calls
    assert all(timeout is not None and timeout <= 1.0 for timeout in calls)
