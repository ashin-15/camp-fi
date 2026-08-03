import httpx
import logging
import json
import re
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from pathlib import Path
from ..portals.iiitk import IIITKAdapter
from ..portals.fortinet import FortinetAdapter
from .probes import check_connectivity, ConnectivityStatus

logger = logging.getLogger("camp-fi")

ADAPTERS = [FortinetAdapter(), IIITKAdapter()]

def save_cookies(client: httpx.Client, path: Path):
    cookies = {cookie.name: cookie.value for cookie in client.cookies.jar}
    with path.open("w") as f:
        json.dump(cookies, f)

def load_cookies(client: httpx.Client, path: Path, url: str):
    if path.exists():
        with path.open("r") as f:
            cookies = json.load(f)
            for k, v in cookies.items():
                client.cookies.set(k, v, domain=httpx.URL(url).host)

def execute_login(redirect_url: str, username: str, password: str, cookies_path: Path | None = None) -> tuple[bool, int | None, str | None]:
    """Execute portal login sequence and return (success, keepalive_interval)."""
    with httpx.Client(follow_redirects=True, verify=False) as client:
        if cookies_path:
            load_cookies(client, cookies_path, redirect_url)
            
        try:
            resp = client.get(redirect_url)
            resp.raise_for_status()
            html = resp.text
            final_url = str(resp.url)
            
            # Follow HTML/JS redirects up to 3 times
            for _ in range(3):
                next_url = None
                
                # Check Meta Refresh
                soup = BeautifulSoup(html, "html.parser")
                meta = soup.find("meta", attrs={"http-equiv": lambda x: x and x.lower() == "refresh"})
                if meta:
                    content = meta.get("content", "")
                    m = re.match(r"(\d+)(?:\s*;\s*url=(.*))?", content, re.IGNORECASE)
                    if m and m.group(2):
                        next_url = m.group(2).strip("'\" ")
                
                # Check JS window.location
                if not next_url:
                    js_m = re.search(r'window\.location(?:\.href)?\s*=\s*[\'"]([^\'"]+)[\'"]', html)
                    if js_m:
                        next_url = js_m.group(1)
                        
                if next_url:
                    final_url = urljoin(final_url, next_url)
                    logger.info(f"Following HTML/JS redirect to {final_url}")
                    resp = client.get(final_url)
                    resp.raise_for_status()
                    html = resp.text
                    final_url = str(resp.url)
                else:
                    break
            
            adapter = next((a for a in ADAPTERS if a.matches(html, final_url)), None)
            
            # Fallback for IIITK if adapter fails or no form
            if not adapter or "auth.iiitkottayam.ac.in" not in final_url:
                logger.info("Attempting explicit fallback to https://auth.iiitkottayam.ac.in")
                resp = client.get("https://auth.iiitkottayam.ac.in")
                resp.raise_for_status()
                html = resp.text
                final_url = str(resp.url)
                adapter = ADAPTERS[0]
                
            prepared = adapter.prepare_login(client, html, final_url)
            login_resp = adapter.submit_login(client, prepared, username, password)
            login_resp.raise_for_status()
            
            if cookies_path:
                save_cookies(client, cookies_path)
                
            # Verify with probe
            probe = check_connectivity()
            if probe.status == ConnectivityStatus.INTERNET:
                logger.info("Login successful. Internet connectivity verified.")
                keepalive_interval, keepalive_url = adapter.keepalive(client, login_resp.text, str(login_resp.url))
                return True, keepalive_interval, keepalive_url
            else:
                logger.warning(f"Login submitted but no internet. Probe status: {probe.status}")
                return False, None, None
                
        except Exception as e:
            logger.error(f"Login failed: {e}")
            return False, None, None
