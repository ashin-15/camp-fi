import httpx
import logging
import re
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from pathlib import Path
from ..portals.iiitk import IIITKAdapter
from ..portals.fortinet import FortinetAdapter
from ..portals.generic_form import GenericFormAdapter
from ..models import LoginResult, LoginStatus, KeepaliveSpec
from .probes import check_connectivity, ConnectivityStatus
from .http_client import build_http_client
from ..session_store import save_cookies, load_cookies

logger = logging.getLogger("camp-fi")

ADAPTERS = [FortinetAdapter(), IIITKAdapter(), GenericFormAdapter()]

def execute_login(
    redirect_url: str,
    username: str,
    password: str,
    cookies_path: Path | None = None,
    probe_fn=check_connectivity,
    verify: bool = True,
) -> LoginResult:
    """Execute portal login sequence and return a LoginResult."""
    with build_http_client(follow_redirects=True, verify=verify) as client:
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
                    logger.info("Following HTML/JS redirect to %s", final_url)
                    resp = client.get(final_url)
                    resp.raise_for_status()
                    html = resp.text
                    final_url = str(resp.url)
                else:
                    break
            
            adapter = next((a for a in ADAPTERS if a.matches(html, final_url)), None)
            if not adapter:
                logger.warning("No matching portal adapter found.")
                return LoginResult(
                    status=LoginStatus.UNSUPPORTED_PORTAL,
                    message="No supported login form or portal adapter was found.",
                )
                
            logger.info("Using portal adapter '%s'.", adapter.name)
            prepared = adapter.prepare_login(client, html, final_url)
            logger.info("Passing credentials for user '%s' via '%s' adapter.", username, adapter.name)
            login_resp = adapter.submit_login(client, prepared, username, password)
            login_resp.raise_for_status()
            if cookies_path:
                save_cookies(client, cookies_path)
                
            # Verify with probe
            probe = probe_fn()
            if probe.status == ConnectivityStatus.INTERNET:
                logger.info("Login successful. Internet connectivity verified.")
                keepalive = adapter.get_keepalive(client, login_resp.text, str(login_resp.url))
                return LoginResult(
                    status=LoginStatus.SUCCESS,
                    adapter_name=adapter.name,
                    keepalive=keepalive,
                )
            else:
                logger.warning("Login submitted but no internet. Probe status: %s", probe.status)
                return LoginResult(
                    status=LoginStatus.AUTH_FAILED,
                    adapter_name=adapter.name,
                    message=f"Login submitted but probe status was {probe.status.name}",
                )
                
        except httpx.RequestError as e:
            logger.error("Network error during login: %s", e)
            return LoginResult(status=LoginStatus.NETWORK_ERROR, message=str(e))
        except Exception as e:
            logger.error("Login failed: %s", e)
            return LoginResult(status=LoginStatus.PROTOCOL_ERROR, message=str(e))
