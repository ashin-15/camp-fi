import logging
import signal
import threading
import time

from .config import load_config
from .credentials import get_password
from .daemon_state import DaemonState
from .history import record_event
from .net.captive import execute_login
from .net.http_client import build_http_client
from .net.probes import ConnectivityStatus, check_connectivity
from .net.ssid import get_current_ssid
from .notify import notify
from .paths import get_cookie_path, get_history_path, get_live_state_path
from .session_store import write_private_json

logger = logging.getLogger("camp-fi")

def run_daemon(foreground: bool = False, stop_event: threading.Event | None = None):
    config = load_config()
    state = DaemonState()
    if stop_event is None:
        stop_event = threading.Event()

    def stop_handler(signum, frame):
        logger.info("Received signal %s. Shutting down daemon...", signum)
        stop_event.set()

    try:
        signal.signal(signal.SIGINT, stop_handler)
        signal.signal(signal.SIGTERM, stop_handler)
    except ValueError:
        # Signals can only be set from the main thread
        pass

    logger.info("Starting camp-fi daemon loop...")

    while not stop_event.is_set():
        ssid = get_current_ssid()
        if not ssid:
            if stop_event.wait(10):
                break
            continue
            
        active_profile_name = None
        for name, profile in config.profiles.items():
            if ssid in profile.ssids:
                active_profile_name = name
                break
                
        if not active_profile_name:
            if stop_event.wait(30):
                break
            continue
            
        state.active_profile = active_profile_name
        profile = config.profiles[active_profile_name]
        password = get_password(active_profile_name, profile.username)
        if not password:
            logger.error("No password for profile '%s', user '%s'.", active_profile_name, profile.username)
            if stop_event.wait(60):
                break
            continue
            
        probe = check_connectivity()
        state.last_status = probe.status
        write_private_json(get_live_state_path(), state.to_dict())
        now = time.time()
        
        if probe.status == ConnectivityStatus.INTERNET:
            state.reset_backoff()
            if state.is_keepalive_due(now):
                if state.keepalive_url:
                    logger.info("Pinging keepalive URL: %s", state.keepalive_url)
                    try:
                        with build_http_client(timeout=5.0, follow_redirects=True) as c:
                            c.get(state.keepalive_url)
                    except Exception as e:
                        logger.warning("Keepalive ping failed: %s", e)
                state.last_keepalive_time = now
            if stop_event.wait(15):
                break
        elif probe.status == ConnectivityStatus.CAPTIVE:
            logger.info("Captive portal detected at %s. Logging in...", probe.redirect_url)
            record_event(get_history_path(), "captive_detected", active_profile_name)
            cookies_path = get_cookie_path(active_profile_name)
            
            login_result = execute_login(probe.redirect_url, profile.username, password, cookies_path)
            had_failures = state.consecutive_failures > 0
            state.update_from_login(login_result, now, profile)
            write_private_json(get_live_state_path(), state.to_dict())
            record_event(
                get_history_path(),
                "login_success" if login_result.succeeded else "login_failed",
                active_profile_name,
                login_result,
            )
            
            if login_result.succeeded:
                logger.info("Successfully authenticated via adapter '%s'.", login_result.adapter_name)
                if had_failures:
                    notify("camp-fi", f"Reconnected via {login_result.adapter_name}")
            else:
                logger.warning("Login failed (%s). Backing off for %s seconds.", login_result.message, state.backoff_seconds)
                if state.consecutive_failures == 3:
                    notify("camp-fi: login failing", login_result.message or "Login failed", urgency="critical")
                if stop_event.wait(state.backoff_seconds):
                    break
        else:
            if stop_event.wait(10):
                break
