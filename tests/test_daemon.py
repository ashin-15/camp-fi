from camp_fi.daemon_state import DaemonState
from camp_fi.models import LoginResult, LoginStatus, KeepaliveSpec

def test_daemon_state_backoff():
    state = DaemonState()
    assert state.backoff_seconds == 5

    res = LoginResult(status=LoginStatus.AUTH_FAILED, message="bad pass")
    state.update_from_login(res, now=100.0)
    assert state.backoff_seconds == 10

    state.update_from_login(res, now=105.0)
    assert state.backoff_seconds == 20

    success = LoginResult(status=LoginStatus.SUCCESS, adapter_name="iiitk", keepalive=KeepaliveSpec("http://k.local", 600))
    state.update_from_login(success, now=110.0)
    assert state.backoff_seconds == 5
    assert state.keepalive_interval == 600
    assert state.keepalive_url == "http://k.local"

def test_keepalive_clamping():
    state = DaemonState()
    success_too_short = LoginResult(status=LoginStatus.SUCCESS, keepalive=KeepaliveSpec("http://k.local", 10))
    state.update_from_login(success_too_short, now=100.0)
    assert state.keepalive_interval == 45

    success_too_long = LoginResult(status=LoginStatus.SUCCESS, keepalive=KeepaliveSpec("http://k.local", 99999))
    state.update_from_login(success_too_long, now=100.0)
    assert state.keepalive_interval == 3600

import sys
import time
import signal
import subprocess

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
        raise AssertionError(f"Daemon failed to shutdown promptly on SIGINT (exceeded 2.0s timeout)")
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
        raise AssertionError(f"Daemon failed to shutdown promptly on SIGTERM (exceeded 2.0s timeout)")
    elapsed = time.time() - start
    assert elapsed < 1.0, f"Shutdown took {elapsed:.2f}s, expected < 1.0s"

import threading
from unittest.mock import patch
import camp_fi.daemon
from camp_fi.net.probes import ProbeResult, ConnectivityStatus
from camp_fi.config import AppConfig, ProfileConfig

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
