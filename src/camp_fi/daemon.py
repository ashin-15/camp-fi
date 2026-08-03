import time
import logging
from .config import load_config
from .credentials import get_password
from .net.ssid import get_current_ssid
from .net.probes import check_connectivity, ConnectivityStatus
from .net.captive import execute_login
from .paths import get_cookie_path

logger = logging.getLogger("camp-fi")

def run_daemon(foreground: bool = False):
    config = load_config()
    
    backoff = 5
    max_backoff = 300
    keepalive_interval = 300
    last_keepalive_time = 0
    
    logger.info("Starting camp-fi daemon loop...")
    
    while True:
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
            
        profile = config.profiles[active_profile_name]
        password = get_password(active_profile_name, profile.username)
        if not password:
            logger.error(f"No password for profile '{active_profile_name}', user '{profile.username}'.")
            time.sleep(60)
            continue
            
        probe = check_connectivity()
        
        if probe.status == ConnectivityStatus.INTERNET:
            backoff = 5
            now = time.time()
            if keepalive_interval and (now - last_keepalive_time) >= keepalive_interval:
                logger.info("Keepalive triggered (via dummy probe/login update).")
                # Usually keepalive means hitting a specific URL. 
                # If we don't have it, we just sleep. The captive module can be expanded to return keepalive URL.
                last_keepalive_time = now
            time.sleep(15)
            
        elif probe.status == ConnectivityStatus.CAPTIVE:
            logger.info(f"Captive portal detected at {probe.redirect_url}. Logging in...")
            cookies_path = get_cookie_path(active_profile_name)
            
            success, new_interval = execute_login(probe.redirect_url, profile.username, password, cookies_path)
            
            if success:
                logger.info("Successfully authenticated.")
                backoff = 5
                if new_interval:
                    keepalive_interval = new_interval
                last_keepalive_time = time.time()
            else:
                logger.warning(f"Login failed. Backing off for {backoff} seconds.")
                time.sleep(backoff)
                backoff = min(backoff * 2, max_backoff)
                
        else:
            time.sleep(10)
