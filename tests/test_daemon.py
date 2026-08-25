import signal
import subprocess
import sys
import threading
import time
from unittest.mock import patch

import camp_fi.daemon
from camp_fi.config import AppConfig, ProfileConfig
from camp_fi.daemon_state import DaemonState
from camp_fi.models import KeepaliveSpec, LoginResult, LoginStatus
from camp_fi.net.probes import ConnectivityStatus, ProbeResult


def test_daemon_state_backoff():
    state = DaemonState()
    assert state.backoff_seconds == 5
    assert state.consecutive_failures == 0

    res = LoginResult(status=LoginStatus.AUTH_FAILED, message="bad pass")
    state.update_from_login(res, now=100.0)
    assert state.backoff_seconds == 10
    assert state.consecutive_failures == 1

    state.update_from_login(res, now=105.0)
    assert state.backoff_seconds == 20
    assert state.consecutive_failures == 2

    success = LoginResult(status=LoginStatus.SUCCESS, adapter_name="iiitk", keepalive=KeepaliveSpec("http://k.local", 600))
    state.update_from_login(success, now=110.0)
    assert state.backoff_seconds == 5
    assert state.consecutive_failures == 0
    assert state.keepalive_interval == 600
    assert state.keepalive_url == "http://k.local"

def test_daemon_state_consecutive_failures():
    state = DaemonState()
    assert state.consecutive_failures == 0
    state.increase_backoff()
    assert state.consecutive_failures == 1
    state.increase_backoff()
    assert state.consecutive_failures == 2
    state.reset_backoff()
    assert state.consecutive_failures == 0
def test_keepalive_clamping():
    state = DaemonState()
    success_too_short = LoginResult(status=LoginStatus.SUCCESS, keepalive=KeepaliveSpec("http://k.local", 10))
    state.update_from_login(success_too_short, now=100.0)
    assert state.keepalive_interval == 45

    success_too_long = LoginResult(status=LoginStatus.SUCCESS, keepalive=KeepaliveSpec("http://k.local", 99999))
    state.update_from_login(success_too_long, now=100.0)
    assert state.keepalive_interval == 3600


def test_update_from_login_profile_fallback():
    state = DaemonState()
    profile = ProfileConfig(
        username="testuser",
        ssids=["TestSSID"],
        keepalive_url="http://manual.override/ping",
        keepalive_interval_seconds=150,
    )
    success_no_keepalive = LoginResult(status=LoginStatus.SUCCESS, adapter_name="custom", keepalive=None)
    state.update_from_login(success_no_keepalive, now=100.0, profile=profile)

    assert state.backoff_seconds == 5
    assert state.keepalive_url == "http://manual.override/ping"
    assert state.keepalive_interval == 150


def test_update_from_login_profile_clamping():
    state = DaemonState()
    profile_short = ProfileConfig(
        username="testuser",
        ssids=["TestSSID"],
        keepalive_url="http://manual.override/ping",
        keepalive_interval_seconds=15,
    )
    success_no_keepalive = LoginResult(status=LoginStatus.SUCCESS, keepalive=None)
    state.update_from_login(success_no_keepalive, now=100.0, profile=profile_short)
    assert state.keepalive_interval == 45

    profile_long = ProfileConfig(
        username="testuser",
        ssids=["TestSSID"],
        keepalive_url="http://manual.override/ping",
        keepalive_interval_seconds=10000,
    )
    state.update_from_login(success_no_keepalive, now=100.0, profile=profile_long)
    assert state.keepalive_interval == 3600


def test_update_from_login_prefers_detected_over_profile():
    state = DaemonState()
    profile = ProfileConfig(
        username="testuser",
        ssids=["TestSSID"],
        keepalive_url="http://manual.override/ping",
        keepalive_interval_seconds=600,
    )
    detected_keepalive = KeepaliveSpec("http://detected.portal/keepalive", 120)
    success_with_keepalive = LoginResult(
        status=LoginStatus.SUCCESS,
        adapter_name="fortinet",
        keepalive=detected_keepalive,
    )
    state.update_from_login(success_with_keepalive, now=100.0, profile=profile)

    assert state.keepalive_url == "http://detected.portal/keepalive"
    assert state.keepalive_interval == 120
def test_daemon_shutdown_latency_on_sigint():
    code = """
from unittest.mock import patch
import camp_fi.daemon
from camp_fi.net.probes import ProbeResult, ConnectivityStatus
from camp_fi.config import AppConfig, ProfileConfig

dummy_config = AppConfig(profiles={
    "test": ProfileConfig(username="testuser", ssids=["TestSSID"])
})

with patch("camp_fi.daemon.load_config", return_value=dummy_config), \\
     patch("camp_fi.daemon.get_current_ssid", return_value="TestSSID"), \\
     patch("camp_fi.daemon.get_password", return_value="testpass"), \\
     patch("camp_fi.daemon.check_connectivity", return_value=ProbeResult(ConnectivityStatus.INTERNET)):
    camp_fi.daemon.run_daemon()
"""
    proc = subprocess.Popen([sys.executable, "-c", code], text=True)
    time.sleep(0.5)
    start = time.time()
    proc.send_signal(signal.SIGINT)
    try:
        proc.wait(timeout=2.0)
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.wait()
        raise AssertionError("Daemon failed to shutdown promptly on SIGINT (exceeded 2.0s timeout)")
    elapsed = time.time() - start
    assert elapsed < 1.0, f"Shutdown took {elapsed:.2f}s, expected < 1.0s"

def test_daemon_shutdown_latency_on_sigterm():
    code = """
from unittest.mock import patch
import camp_fi.daemon
from camp_fi.net.probes import ProbeResult, ConnectivityStatus
from camp_fi.config import AppConfig, ProfileConfig

dummy_config = AppConfig(profiles={
    "test": ProfileConfig(username="testuser", ssids=["TestSSID"])
})

with patch("camp_fi.daemon.load_config", return_value=dummy_config), \\
     patch("camp_fi.daemon.get_current_ssid", return_value="TestSSID"), \\
     patch("camp_fi.daemon.get_password", return_value="testpass"), \\
     patch("camp_fi.daemon.check_connectivity", return_value=ProbeResult(ConnectivityStatus.INTERNET)):
    camp_fi.daemon.run_daemon()
"""
    proc = subprocess.Popen([sys.executable, "-c", code], text=True)
    time.sleep(0.5)
    start = time.time()
    proc.send_signal(signal.SIGTERM)
    try:
        proc.wait(timeout=2.0)
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.wait()
        raise AssertionError("Daemon failed to shutdown promptly on SIGTERM (exceeded 2.0s timeout)")
    elapsed = time.time() - start
    assert elapsed < 1.0, f"Shutdown took {elapsed:.2f}s, expected < 1.0s"

def test_daemon_stop_event_direct():
    dummy_config = AppConfig(profiles={
        "test": ProfileConfig(username="testuser", ssids=["TestSSID"])
    })
    stop_event = threading.Event()

    with patch("camp_fi.daemon.load_config", return_value=dummy_config), \
         patch("camp_fi.daemon.get_current_ssid", return_value="TestSSID"), \
         patch("camp_fi.daemon.get_password", return_value="testpass"), \
         patch("camp_fi.daemon.check_connectivity", return_value=ProbeResult(ConnectivityStatus.INTERNET)):
        
        t = threading.Thread(target=camp_fi.daemon.run_daemon, kwargs={"stop_event": stop_event})
        t.start()
        time.sleep(0.05)
        start = time.time()
        stop_event.set()
        t.join(timeout=0.5)
        elapsed = time.time() - start
        assert not t.is_alive(), "Daemon thread did not terminate within timeout"
        assert elapsed < 0.2, f"Shutdown took {elapsed:.2f}s, expected < 0.2s"

def test_daemon_notifies_on_third_consecutive_failure():
    dummy_config = AppConfig(profiles={
        "test": ProfileConfig(username="testuser", ssids=["TestSSID"])
    })
    stop_event = threading.Event()
    attempts = 0

    def mock_login(*args, **kwargs):
        nonlocal attempts
        attempts += 1
        if attempts >= 3:
            stop_event.set()
        return LoginResult(status=LoginStatus.AUTH_FAILED, message="Invalid credentials")

    with patch("camp_fi.daemon.load_config", return_value=dummy_config), \
         patch("camp_fi.daemon.get_current_ssid", return_value="TestSSID"), \
         patch("camp_fi.daemon.get_password", return_value="testpass"), \
         patch("camp_fi.daemon.check_connectivity", return_value=ProbeResult(ConnectivityStatus.CAPTIVE, redirect_url="http://login.local")), \
         patch("camp_fi.daemon.execute_login", side_effect=mock_login), \
         patch("camp_fi.daemon.record_event"), \
         patch("camp_fi.daemon.notify") as mock_notify, \
         patch.object(stop_event, "wait", side_effect=lambda timeout: stop_event.is_set()):
        camp_fi.daemon.run_daemon(stop_event=stop_event)

    assert attempts == 3
    mock_notify.assert_called_once_with("camp-fi: login failing", "Invalid credentials", urgency="critical")


def test_daemon_reconnect_notification_after_prior_failure():
    dummy_config = AppConfig(profiles={
        "test": ProfileConfig(username="testuser", ssids=["TestSSID"])
    })
    stop_event = threading.Event()
    results = [
        LoginResult(status=LoginStatus.AUTH_FAILED, message="Temporary failure"),
        LoginResult(status=LoginStatus.SUCCESS, adapter_name="iiitk"),
    ]

    def mock_login(*args, **kwargs):
        res = results.pop(0)
        if not results:
            stop_event.set()
        return res

    with patch("camp_fi.daemon.load_config", return_value=dummy_config), \
         patch("camp_fi.daemon.get_current_ssid", return_value="TestSSID"), \
         patch("camp_fi.daemon.get_password", return_value="testpass"), \
         patch("camp_fi.daemon.check_connectivity", return_value=ProbeResult(ConnectivityStatus.CAPTIVE, redirect_url="http://login.local")), \
         patch("camp_fi.daemon.execute_login", side_effect=mock_login), \
         patch("camp_fi.daemon.record_event"), \
         patch("camp_fi.daemon.notify") as mock_notify, \
         patch.object(stop_event, "wait", side_effect=lambda timeout: stop_event.is_set()):
        camp_fi.daemon.run_daemon(stop_event=stop_event)

    mock_notify.assert_called_once_with("camp-fi", "Reconnected via iiitk")


def test_daemon_no_reconnect_notification_on_initial_success():
    dummy_config = AppConfig(profiles={
        "test": ProfileConfig(username="testuser", ssids=["TestSSID"])
    })
    stop_event = threading.Event()

    def mock_login(*args, **kwargs):
        stop_event.set()
        return LoginResult(status=LoginStatus.SUCCESS, adapter_name="iiitk")

    with patch("camp_fi.daemon.load_config", return_value=dummy_config), \
         patch("camp_fi.daemon.get_current_ssid", return_value="TestSSID"), \
         patch("camp_fi.daemon.get_password", return_value="testpass"), \
         patch("camp_fi.daemon.check_connectivity", return_value=ProbeResult(ConnectivityStatus.CAPTIVE, redirect_url="http://login.local")), \
         patch("camp_fi.daemon.execute_login", side_effect=mock_login), \
         patch("camp_fi.daemon.record_event"), \
         patch("camp_fi.daemon.notify") as mock_notify, \
         patch.object(stop_event, "wait", side_effect=lambda timeout: stop_event.is_set()):
        camp_fi.daemon.run_daemon(stop_event=stop_event)

    mock_notify.assert_not_called()


def test_daemon_state_to_dict():
    state = DaemonState(
        active_profile="iiitk",
        backoff_seconds=10,
        consecutive_failures=2,
        last_status=ConnectivityStatus.CAPTIVE,
        keepalive_interval=120,
        last_keepalive_time=123456.0,
    )
    d = state.to_dict()
    assert d["active_profile"] == "iiitk"
    assert d["backoff_seconds"] == 10
    assert d["consecutive_failures"] == 2
    assert d["last_status"] == "CAPTIVE"
    assert d["keepalive_interval"] == 120
    assert d["last_keepalive_time"] == 123456.0
    assert isinstance(d["updated_at"], float)
    assert d["updated_at"] > 0


def test_get_live_state_path(tmp_path, monkeypatch):
    from camp_fi.paths import get_live_state_path
    monkeypatch.setattr("camp_fi.paths.get_state_dir", lambda: tmp_path)
    assert get_live_state_path() == tmp_path / "daemon_live_state.json"


def test_daemon_writes_live_state(tmp_path, monkeypatch):
    import json
    monkeypatch.setattr("camp_fi.paths.get_config_dir", lambda: tmp_path)
    monkeypatch.setattr("camp_fi.paths.get_state_dir", lambda: tmp_path)

    dummy_config = AppConfig(profiles={
        "test": ProfileConfig(username="testuser", ssids=["TestSSID"])
    })
    stop_event = threading.Event()

    def mock_check():
        stop_event.set()
        return ProbeResult(ConnectivityStatus.INTERNET)

    with patch("camp_fi.daemon.load_config", return_value=dummy_config), \
         patch("camp_fi.daemon.get_current_ssid", return_value="TestSSID"), \
         patch("camp_fi.daemon.get_password", return_value="testpass"), \
         patch("camp_fi.daemon.check_connectivity", side_effect=mock_check), \
         patch.object(stop_event, "wait", side_effect=lambda timeout: stop_event.is_set()):
        camp_fi.daemon.run_daemon(stop_event=stop_event)

    live_file = tmp_path / "daemon_live_state.json"
    assert live_file.exists()
    data = json.loads(live_file.read_text())
    assert data["active_profile"] == "test"
    assert data["last_status"] == "INTERNET"
    assert data["consecutive_failures"] == 0
