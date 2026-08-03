import httpx
import re
import logging
from typing import Any
from .base import PortalAdapter
from ..keepalive import parse_keepalive

logger = logging.getLogger("camp-fi")

class FortinetAdapter:
    def matches(self, html: str, url: str) -> bool:
        return "magic" in html.lower() and ("auth.iiitkottayam.ac.in" in url or ":1000" in url)
        
    def prepare_login(self, client: httpx.Client, html: str, url: str) -> dict[str, Any]:
        m = re.search(r'name="?magic"?\s+value="?([a-zA-Z0-9]+)"?', html, re.IGNORECASE)
        if not m:
            raise ValueError("No magic token found in Fortinet portal page")
        magic = m.group(1)
        
        base_url = re.sub(r'\?.*$', '', url)
        logout_url = base_url.replace("/login", "/logout") if "/login" in base_url else base_url + "/logout"
        
        return {
            "magic": magic,
            "login_url": base_url,
            "logout_url": logout_url
        }
        
    def submit_login(self, client: httpx.Client, prepared_data: dict[str, Any], username: str, password: str) -> httpx.Response:
        logout_url_with_magic = f"{prepared_data['logout_url']}?{prepared_data['magic']}"
        
        try:
            logger.info("Executing pre-emptive logout to clear stale sessions...")
            client.get(logout_url_with_magic, timeout=3.0)
        except Exception:
            pass
            
        data = {
            "magic": prepared_data["magic"],
            "username": username,
            "password": password
        }
        
        req = client.build_request("POST", prepared_data["login_url"], data=data)
        return client.send(req)
        
    def keepalive(self, client: httpx.Client, html: str, url: str) -> tuple[int | None, str | None]:
        ki = parse_keepalive(html, url)
        if ki:
            return ki.interval, ki.url
        return 1800, None
