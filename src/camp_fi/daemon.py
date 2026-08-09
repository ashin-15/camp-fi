import time
import signal
import logging
from .config import load_config
from .credentials import get_password
from .net.ssid import get_current_ssid
from .net.probes import check_connectivity, ConnectivityStatus
from .net.captive import execute_login
from .net.http_client import build_http_client
from .paths import get_cookie_path
from .daemon_state import DaemonState

logger = logging.getLogger("camp-fi")

def run_daemon(foreground: bool = False):
    config = load_config()
    state = DaemonState()
    running = True

    def stop_handler(signum, frame):
        nonlocal running
        logger.info(f"Received signal {signum}. Shutting down daemon...")
        running = False

    signal.signal(signal.SIGINT, stop_handler)
    signal.signal(signal.SIGTERM, stop_handler)

    logger.info("Starting camp-fi daemon loop...")

    while running:
        ssid = get_current_ssid()
        if not ssid:
            time.sleep(10)
            continue
            
        active_profile_name = None
        for name, profile in config.profiles.items():
            if ssid in profile.ssids:
                active_profile_name = name
                break
                
        if not active_profile_name:
            time.sleep(30)
            continue
            
        state.active_profile = active_profile_name
        profile = config.profiles[active_profile_name]
        password = get_password(active_profile_name, profile.username)
        if not password:
            logger.error(f"No password for profile '{active_profile_name}', user '{profile.username}'.")
            time.sleep(60)
            continue
            
        probe = check_connectivity()
        state.last_status = probe.status
        now = time.time()
        
        if probe.status == ConnectivityStatus.INTERNET:
            state.reset_backoff()
            if state.is_keepalive_due(now):
                if state.keepalive_url:
                    logger.info(f"Pinging keepalive URL: {state.keepalive_url}")
                    try:
                        with build_http_client(timeout=5.0, follow_redirects=True) as c:
                            c.get(state.keepalive_url)
                    except Exception as e:
                        logger.warning(f"Keepalive ping failed: {e}")
                state.last_keepalive_time = now
            time.sleep(15)
            
        elif probe.status == ConnectivityStatus.CAPTIVE:
            logger.info(f"Captive portal detected at {probe.redirect_url}. Logging in...")
            cookies_path = get_cookie_path(active_profile_name)
            
            login_result = execute_login(probe.redirect_url, profile.username, password, cookies_path)
            state.update_from_login(login_result, now)
            
            if login_result.succeeded:
                logger.info(f"Successfully authenticated via adapter '{login_result.adapter_name}'.")
            else:
                logger.warning(f"Login failed ({login_result.message}). Backing off for {state.backoff_seconds} seconds.")
                time.sleep(state.backoff_seconds)
                
        else:
            time.sleep(10)
