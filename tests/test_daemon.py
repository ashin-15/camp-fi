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
