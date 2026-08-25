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
