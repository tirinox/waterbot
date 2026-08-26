import stat

import pytest

from backend.sync_config import (
    DEFAULT_CONFIG_FILE,
    DEFAULT_TARGET_FILE,
    main,
    read_iot_config,
    render_iot_config,
)


def test_default_paths_are_repository_relative():
    assert DEFAULT_CONFIG_FILE.is_absolute()
    assert DEFAULT_CONFIG_FILE.name == "config.yaml"
    assert DEFAULT_TARGET_FILE.is_absolute()
    assert DEFAULT_TARGET_FILE.parts[-2:] == ("iot_code", "private_const.py")


def test_rendered_values_are_valid_escaped_python_literals():
    values = {
        "wifi_ssid": "Owner's network\nsecond line",
        "callback_port": 8080,
        "calibration": 1.25,
        "enabled": True,
    }

    content, names = render_iot_config(values)
    namespace = {}
    exec(content, namespace)

    assert names == ["WIFI_SSID", "CALLBACK_PORT", "CALIBRATION", "ENABLED"]
    assert namespace["WIFI_SSID"] == values["wifi_ssid"]
    assert namespace["CALLBACK_PORT"] == values["callback_port"]
    assert namespace["CALIBRATION"] == values["calibration"]
    assert namespace["ENABLED"] is True


@pytest.mark.parametrize("key", ["wifi-password", "two words", ""])
def test_invalid_constant_names_are_rejected(key):
    with pytest.raises(ValueError, match="valid Python identifier"):
        render_iot_config({key: "value"})


def test_duplicate_generated_constant_names_are_rejected():
    with pytest.raises(ValueError, match="Duplicate generated constant"):
        render_iot_config({"wifi_ssid": "first", "WIFI_SSID": "second"})


@pytest.mark.parametrize("value", [float("inf"), float("-inf"), float("nan")])
def test_non_finite_numbers_are_rejected(value):
    with pytest.raises(ValueError, match="finite number"):
        render_iot_config({"calibration": value})


def test_yaml_errors_do_not_include_file_contents(tmp_path):
    secret = "malformed-secret-value"
    config_path = tmp_path / "config.yaml"
    config_path.write_text(f"iot: [\n  {secret}\n", encoding="utf-8")

    with pytest.raises(ValueError) as error:
        read_iot_config(config_path)

    assert secret not in str(error.value)


def test_dry_run_validates_without_writing_or_printing_secrets(tmp_path, capsys):
    secret = "do-not-print-this-secret"
    config_path = tmp_path / "config.yaml"
    config_path.write_text(
        f"iot:\n  wifi_ssid: test-network\n  shared_secret: {secret}\n",
        encoding="utf-8",
    )
    target_path = tmp_path / "private_const.py"

    result = main(["--config", str(config_path), "--target", str(target_path), "--dry-run"])

    output = capsys.readouterr().out
    assert result == 0
    assert not target_path.exists()
    assert secret not in output
    assert "SHARED_SECRET" in output


def test_sync_writes_private_file_without_printing_values(tmp_path, capsys):
    secret = "another-private-value"
    config_path = tmp_path / "config.yaml"
    config_path.write_text(
        f"iot:\n  callback_host: https://example.test/sensor\n  shared_secret: {secret}\n",
        encoding="utf-8",
    )
    target_path = tmp_path / "device" / "private_const.py"

    result = main(["--config", str(config_path), "--target", str(target_path)])

    output = capsys.readouterr().out
    assert result == 0
    assert secret not in output
    assert secret in target_path.read_text(encoding="utf-8")
    assert stat.S_IMODE(target_path.stat().st_mode) == 0o600
