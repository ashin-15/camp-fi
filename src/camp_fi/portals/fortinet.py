import httpx
import re
import logging
from .generic_form import parse_login_form
from ..keepalive import parse_keepalive
from ..models import PreparedLogin, KeepaliveSpec

logger = logging.getLogger("camp-fi")

class FortinetAdapter:
    name = "fortinet"

    def matches(self, html: str, url: str) -> bool:
        return "magic" in html.lower() and ("auth.iiitkottayam.ac.in" in url.lower() or ":1000" in url or "fortinet" in html.lower() or "fgtauth" in html.lower())
        
    def prepare_login(self, client: httpx.Client, html: str, url: str) -> PreparedLogin:
        m = re.search(r'name="?magic"?\s+value="?([a-zA-Z0-9]+)"?', html, re.IGNORECASE)
        if not m:
            raise ValueError("No magic token found in Fortinet portal page")
        magic = m.group(1)
        
        base_url = re.sub(r'\?.*$', '', url)
        logout_url = base_url.replace("/login", "/logout") if "/login" in base_url else base_url + "/logout"
        
        return PreparedLogin(data={
            "magic": magic,
            "login_url": base_url,
            "logout_url": logout_url
        })
        
    def submit_login(self, client: httpx.Client, prepared: PreparedLogin, username: str, password: str) -> httpx.Response:
        magic = prepared.data["magic"]
        login_url = prepared.data["login_url"]
        logout_url = prepared.data["logout_url"]
        
        logout_url_with_magic = f"{logout_url}?{magic}"
        
        try:
            logger.info("Executing pre-emptive logout to clear stale sessions...")
            client.get(logout_url_with_magic, timeout=3.0)
        except Exception:
            pass
            
        data = {
            "magic": magic,
            "username": username,
            "password": password
        }
        
        req = client.build_request("POST", login_url, data=data)
        return client.send(req)
        
    def get_keepalive(self, client: httpx.Client, html: str, url: str) -> KeepaliveSpec | None:
        ki = parse_keepalive(html, url)
        if ki:
            return KeepaliveSpec(url=ki.url, interval_seconds=ki.interval)
        return KeepaliveSpec(url=url, interval_seconds=1800)
