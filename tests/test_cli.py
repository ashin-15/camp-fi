from typer.testing import CliRunner

from camp_fi.cli import app

runner = CliRunner()

def test_cli_help():
    res = runner.invoke(app, ["--help"])
    assert res.exit_code == 0
    assert "Wi-Fi Captive Portal Auto-Login Daemon" in res.output

def test_cli_init():
    res = runner.invoke(app, ["init"])
    assert res.exit_code == 0
    assert "Initialization check complete" in res.output

def test_cli_profile_lifecycle(tmp_path, monkeypatch):
    monkeypatch.setattr("camp_fi.paths.get_config_dir", lambda: tmp_path)
    monkeypatch.setattr("camp_fi.paths.get_state_dir", lambda: tmp_path)

    # List default
    res = runner.invoke(app, ["profile", "list"])
    assert res.exit_code == 0

    # Add profile
    res = runner.invoke(app, ["profile", "add", "work"])
    assert res.exit_code == 0
    assert "Profile 'work' created." in res.output

    # Show profile
    res = runner.invoke(app, ["profile", "show", "work"])
    assert res.exit_code == 0
    assert "Profile: work" in res.output

def test_cli_status(tmp_path, monkeypatch):
    monkeypatch.setattr("camp_fi.paths.get_config_dir", lambda: tmp_path)
    monkeypatch.setattr("camp_fi.paths.get_state_dir", lambda: tmp_path)

    res = runner.invoke(app, ["status"])
    assert res.exit_code == 0
    assert "=== camp-fi status ===" in res.output

def test_cli_history(tmp_path, monkeypatch):
    from camp_fi.history import record_event
    from camp_fi.models import LoginResult, LoginStatus

    monkeypatch.setattr("camp_fi.paths.get_state_dir", lambda: tmp_path)
    record_event(tmp_path / "history.jsonl", "login_failed", "iiitk", LoginResult(LoginStatus.AUTH_FAILED, "test", message="bad pass"))

    res = runner.invoke(app, ["history", "--limit", "1"])

    assert res.exit_code == 0
    assert "login_failed profile=iiitk adapter=test status=AUTH_FAILED bad pass" in res.output

def test_cli_keepalive_set(tmp_path, monkeypatch):
    monkeypatch.setattr("camp_fi.paths.get_config_dir", lambda: tmp_path)
    monkeypatch.setattr("camp_fi.paths.get_state_dir", lambda: tmp_path)

    # Create a profile first
    res = runner.invoke(app, ["profile", "add", "custom"])
    assert res.exit_code == 0

    # Set keepalive URL and interval
    res = runner.invoke(
        app,
        [
            "config",
            "keepalive",
            "set",
            "--profile",
            "custom",
            "--url",
            "http://10.0.0.1/ping",
            "--interval",
            "120",
        ],
    )
    assert res.exit_code == 0
    assert "Keepalive settings updated for profile 'custom'." in res.output

    # Verify in profile show
    res = runner.invoke(app, ["profile", "show", "custom"])
    assert res.exit_code == 0
    assert "Keepalive URL: http://10.0.0.1/ping" in res.output
    assert "Keepalive Interval: 120s" in res.output

    # Test non-existent profile
    res = runner.invoke(
        app,
        [
            "config",
            "keepalive",
            "set",
            "--profile",
            "nonexistent",
            "--url",
            "http://10.0.0.1/ping",
        ],
    )
    assert res.exit_code != 0
    assert "Profile 'nonexistent' not found." in res.output


def test_cli_doctor_all_ok(tmp_path, monkeypatch):
    import json
    import time
    from camp_fi.config import AppConfig, ProfileConfig, save_config
    from camp_fi.history import record_event
    from camp_fi.models import LoginResult, LoginStatus
    from camp_fi.net.probes import ConnectivityStatus, ProbeResult

    monkeypatch.setattr("camp_fi.paths.get_config_dir", lambda: tmp_path)
    monkeypatch.setattr("camp_fi.paths.get_state_dir", lambda: tmp_path)

    # Create config with matching profile
    config = AppConfig(profiles={
        "iiitk": ProfileConfig(username="student1", ssids=["IIITKottayam_5G"])
    })
    save_config(config)

    # Setup live state file
    live_state = {
        "active_profile": "iiitk",
        "backoff_seconds": 5,
        "consecutive_failures": 0,
        "last_status": "INTERNET",
        "keepalive_interval": 300,
        "last_keepalive_time": time.time(),
        "updated_at": time.time(),
    }
    (tmp_path / "daemon_live_state.json").write_text(json.dumps(live_state))

    # Add history
    record_event(tmp_path / "history.jsonl", "login_success", "iiitk", LoginResult(LoginStatus.SUCCESS, "iiitk"))

    class MockKeyring:
        pass
    MockKeyring.__name__ = "SecretServiceKeyring"

    monkeypatch.setattr("shutil.which", lambda cmd: "/usr/bin/nmcli" if cmd == "nmcli" else None)
    monkeypatch.setattr("keyring.get_keyring", lambda: MockKeyring())
    monkeypatch.setattr("camp_fi.systemd.is_service_active", lambda: True)
    monkeypatch.setattr("camp_fi.net.ssid.get_current_ssid", lambda: "IIITKottayam_5G")
    monkeypatch.setattr("camp_fi.credentials.get_password", lambda p, u: "pass123")
    monkeypatch.setattr("camp_fi.net.probes.check_connectivity", lambda: ProbeResult(ConnectivityStatus.INTERNET))

    res = runner.invoke(app, ["doctor"])
    assert res.exit_code == 0
    assert "=== camp-fi doctor ===" in res.output
    assert "[OK] Config directory:" in res.output
    assert "[OK] Network detection: nmcli available" in res.output
    assert "[OK] Keyring backend: SecretServiceKeyring" in res.output
    assert "[OK] systemd service: active" in res.output
    assert "Current SSID: IIITKottayam_5G" in res.output
    assert "Matched Profile: iiitk" in res.output
    assert "Connectivity: INTERNET" in res.output
    assert "Credentials Stored: Yes" in res.output
    assert "Active Profile: iiitk" in res.output
    assert "Backoff: 5s (consecutive failures: 0)" in res.output
    assert "login_success profile=iiitk" in res.output
    assert "[OK] All checks passed." in res.output


def test_cli_doctor_json(tmp_path, monkeypatch):
    import json
    import time
    from camp_fi.config import AppConfig, ProfileConfig, save_config
    from camp_fi.history import record_event
    from camp_fi.models import LoginResult, LoginStatus
    from camp_fi.net.probes import ConnectivityStatus, ProbeResult

    monkeypatch.setattr("camp_fi.paths.get_config_dir", lambda: tmp_path)
    monkeypatch.setattr("camp_fi.paths.get_state_dir", lambda: tmp_path)

    config = AppConfig(profiles={
        "iiitk": ProfileConfig(username="student1", ssids=["IIITKottayam_5G"])
    })
    save_config(config)

    live_state = {
        "active_profile": "iiitk",
        "backoff_seconds": 5,
        "consecutive_failures": 0,
        "last_status": "INTERNET",
        "keepalive_interval": 300,
        "last_keepalive_time": time.time(),
        "updated_at": time.time(),
    }
    (tmp_path / "daemon_live_state.json").write_text(json.dumps(live_state))
    record_event(tmp_path / "history.jsonl", "login_success", "iiitk", LoginResult(LoginStatus.SUCCESS, "iiitk"))

    class MockKeyring:
        pass
    MockKeyring.__name__ = "SecretServiceKeyring"

    monkeypatch.setattr("shutil.which", lambda cmd: "/usr/bin/nmcli" if cmd == "nmcli" else None)
    monkeypatch.setattr("keyring.get_keyring", lambda: MockKeyring())
    monkeypatch.setattr("camp_fi.systemd.is_service_active", lambda: True)
    monkeypatch.setattr("camp_fi.net.ssid.get_current_ssid", lambda: "IIITKottayam_5G")
    monkeypatch.setattr("camp_fi.credentials.get_password", lambda p, u: "pass123")
    monkeypatch.setattr("camp_fi.net.probes.check_connectivity", lambda: ProbeResult(ConnectivityStatus.INTERNET))

    res = runner.invoke(app, ["doctor", "--json"])
    assert res.exit_code == 0
    data = json.loads(res.output)
    assert data["warnings"] == []
    assert data["checks"]["ssid_detection"] == "nmcli"
    assert data["checks"]["systemd_service_active"] is True
    assert data["checks"]["current_ssid"] == "IIITKottayam_5G"
    assert data["checks"]["matched_profile"] == "iiitk"
    assert data["checks"]["connectivity_status"] == "INTERNET"
    assert data["checks"]["credentials_stored"] is True
    assert data["checks"]["daemon_state"]["active_profile"] == "iiitk"
    assert len(data["checks"]["recent_attempts"]) == 1


def test_cli_doctor_missing_network_tools(tmp_path, monkeypatch):
    from camp_fi.net.probes import ConnectivityStatus, ProbeResult
    monkeypatch.setattr("camp_fi.paths.get_config_dir", lambda: tmp_path)
    monkeypatch.setattr("camp_fi.paths.get_state_dir", lambda: tmp_path)
    monkeypatch.setattr("shutil.which", lambda cmd: None)
    monkeypatch.setattr("camp_fi.systemd.is_service_active", lambda: None)
    monkeypatch.setattr("camp_fi.net.ssid.get_current_ssid", lambda: None)
    monkeypatch.setattr("camp_fi.net.probes.check_connectivity", lambda: ProbeResult(ConnectivityStatus.INTERNET))

    res = runner.invoke(app, ["doctor"])
    assert res.exit_code == 1
    assert "No nmcli or iwgetid found" in res.output


def test_cli_doctor_keyring_failure(tmp_path, monkeypatch):
    from camp_fi.net.probes import ConnectivityStatus, ProbeResult
    monkeypatch.setattr("camp_fi.paths.get_config_dir", lambda: tmp_path)
    monkeypatch.setattr("camp_fi.paths.get_state_dir", lambda: tmp_path)
    monkeypatch.setattr("shutil.which", lambda cmd: "nmcli")
    monkeypatch.setattr("camp_fi.systemd.is_service_active", lambda: None)
    monkeypatch.setattr("camp_fi.net.ssid.get_current_ssid", lambda: None)
    monkeypatch.setattr("camp_fi.net.probes.check_connectivity", lambda: ProbeResult(ConnectivityStatus.INTERNET))

    class FailKeyring:
        pass
    monkeypatch.setattr("keyring.get_keyring", lambda: FailKeyring())

    res = runner.invoke(app, ["doctor"])
    assert res.exit_code == 1
    assert "Keyring backend appears non-functional" in res.output


def test_cli_doctor_stale_daemon_state(tmp_path, monkeypatch):
    import json
    import time
    from camp_fi.net.probes import ConnectivityStatus, ProbeResult
    monkeypatch.setattr("camp_fi.paths.get_config_dir", lambda: tmp_path)
    monkeypatch.setattr("camp_fi.paths.get_state_dir", lambda: tmp_path)
    monkeypatch.setattr("shutil.which", lambda cmd: "nmcli")
    monkeypatch.setattr("camp_fi.systemd.is_service_active", lambda: None)
    monkeypatch.setattr("camp_fi.net.ssid.get_current_ssid", lambda: None)
    monkeypatch.setattr("camp_fi.net.probes.check_connectivity", lambda: ProbeResult(ConnectivityStatus.INTERNET))

    now = 100000.0
    monkeypatch.setattr("time.time", lambda: now)

    stale_state = {
        "active_profile": "iiitk",
        "backoff_seconds": 5,
        "consecutive_failures": 0,
        "last_status": "INTERNET",
        "updated_at": now - 300,
    }
    (tmp_path / "daemon_live_state.json").write_text(json.dumps(stale_state))

    res = runner.invoke(app, ["doctor"])
    assert res.exit_code == 1
    assert "Daemon state is 300s old — daemon may be stuck or stopped." in res.output


def test_cli_doctor_corrupt_daemon_state(tmp_path, monkeypatch):
    from camp_fi.net.probes import ConnectivityStatus, ProbeResult
    monkeypatch.setattr("camp_fi.paths.get_config_dir", lambda: tmp_path)
    monkeypatch.setattr("camp_fi.paths.get_state_dir", lambda: tmp_path)
    monkeypatch.setattr("shutil.which", lambda cmd: "nmcli")
    monkeypatch.setattr("camp_fi.systemd.is_service_active", lambda: None)
    monkeypatch.setattr("camp_fi.net.ssid.get_current_ssid", lambda: None)
    monkeypatch.setattr("camp_fi.net.probes.check_connectivity", lambda: ProbeResult(ConnectivityStatus.INTERNET))

    (tmp_path / "daemon_live_state.json").write_text("invalid json {")

    res = runner.invoke(app, ["doctor"])
    assert res.exit_code == 1
    assert "Live daemon state file is corrupt." in res.output


def test_cli_doctor_consecutive_failures(tmp_path, monkeypatch):
    import json
    import time
    from camp_fi.net.probes import ConnectivityStatus, ProbeResult
    monkeypatch.setattr("camp_fi.paths.get_config_dir", lambda: tmp_path)
    monkeypatch.setattr("camp_fi.paths.get_state_dir", lambda: tmp_path)
    monkeypatch.setattr("shutil.which", lambda cmd: "nmcli")
    monkeypatch.setattr("camp_fi.systemd.is_service_active", lambda: None)
    monkeypatch.setattr("camp_fi.net.ssid.get_current_ssid", lambda: None)
    monkeypatch.setattr("camp_fi.net.probes.check_connectivity", lambda: ProbeResult(ConnectivityStatus.INTERNET))

    failing_state = {
        "active_profile": "iiitk",
        "backoff_seconds": 40,
        "consecutive_failures": 3,
        "last_status": "CAPTIVE",
        "updated_at": time.time(),
    }
    (tmp_path / "daemon_live_state.json").write_text(json.dumps(failing_state))

    res = runner.invoke(app, ["doctor"])
    assert res.exit_code == 1
    assert "3 consecutive login failures, backoff at 40s." in res.output


def test_cli_doctor_inactive_service(tmp_path, monkeypatch):
    from camp_fi.net.probes import ConnectivityStatus, ProbeResult
    monkeypatch.setattr("camp_fi.paths.get_config_dir", lambda: tmp_path)
    monkeypatch.setattr("camp_fi.paths.get_state_dir", lambda: tmp_path)
    monkeypatch.setattr("shutil.which", lambda cmd: "nmcli")
    monkeypatch.setattr("camp_fi.systemd.is_service_active", lambda: False)
    monkeypatch.setattr("camp_fi.net.ssid.get_current_ssid", lambda: None)
    monkeypatch.setattr("camp_fi.net.probes.check_connectivity", lambda: ProbeResult(ConnectivityStatus.INTERNET))

    res = runner.invoke(app, ["doctor"])
    assert res.exit_code == 1
    assert "systemd service is installed but not running (camp-fi service start)." in res.output


def test_cli_doctor_active_service_missing_state_file(tmp_path, monkeypatch):
    from camp_fi.net.probes import ConnectivityStatus, ProbeResult
    monkeypatch.setattr("camp_fi.paths.get_config_dir", lambda: tmp_path)
    monkeypatch.setattr("camp_fi.paths.get_state_dir", lambda: tmp_path)
    monkeypatch.setattr("shutil.which", lambda cmd: "nmcli")
    monkeypatch.setattr("camp_fi.systemd.is_service_active", lambda: True)
    monkeypatch.setattr("camp_fi.net.ssid.get_current_ssid", lambda: None)
    monkeypatch.setattr("camp_fi.net.probes.check_connectivity", lambda: ProbeResult(ConnectivityStatus.INTERNET))

    res = runner.invoke(app, ["doctor"])
    assert res.exit_code == 1
    assert "Daemon is active but has not written state yet (just started?)." in res.output


def test_cli_doctor_unmatched_ssid(tmp_path, monkeypatch):
    from camp_fi.config import AppConfig, ProfileConfig, save_config
    from camp_fi.net.probes import ConnectivityStatus, ProbeResult
    monkeypatch.setattr("camp_fi.paths.get_config_dir", lambda: tmp_path)
    monkeypatch.setattr("camp_fi.paths.get_state_dir", lambda: tmp_path)
    monkeypatch.setattr("shutil.which", lambda cmd: "nmcli")
    monkeypatch.setattr("camp_fi.systemd.is_service_active", lambda: None)
    monkeypatch.setattr("camp_fi.net.ssid.get_current_ssid", lambda: "UnknownSSID")
    monkeypatch.setattr("camp_fi.net.probes.check_connectivity", lambda: ProbeResult(ConnectivityStatus.INTERNET))

    config = AppConfig(profiles={"iiitk": ProfileConfig(username="user", ssids=["OtherSSID"])})
    save_config(config)

    res = runner.invoke(app, ["doctor"])
    assert res.exit_code == 1
    assert "SSID 'UnknownSSID' doesn't match any configured profile." in res.output


def test_cli_doctor_missing_credentials(tmp_path, monkeypatch):
    from camp_fi.config import AppConfig, ProfileConfig, save_config
    from camp_fi.net.probes import ConnectivityStatus, ProbeResult
    monkeypatch.setattr("camp_fi.paths.get_config_dir", lambda: tmp_path)
    monkeypatch.setattr("camp_fi.paths.get_state_dir", lambda: tmp_path)
    monkeypatch.setattr("shutil.which", lambda cmd: "nmcli")
    monkeypatch.setattr("camp_fi.systemd.is_service_active", lambda: None)
    monkeypatch.setattr("camp_fi.net.ssid.get_current_ssid", lambda: "IIITKottayam_5G")
    monkeypatch.setattr("camp_fi.credentials.get_password", lambda p, u: None)
    monkeypatch.setattr("camp_fi.net.probes.check_connectivity", lambda: ProbeResult(ConnectivityStatus.INTERNET))

    config = AppConfig(profiles={"iiitk": ProfileConfig(username="student1", ssids=["IIITKottayam_5G"])})
    save_config(config)

    res = runner.invoke(app, ["doctor"])
    assert res.exit_code == 1
    assert "No stored credentials for matched profile 'iiitk'." in res.output
