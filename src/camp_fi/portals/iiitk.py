import httpx
from typing import Any
from .base import PortalAdapter
from .generic_form import parse_login_form
from ..keepalive import parse_keepalive

class IIITKAdapter:
    def matches(self, html: str, url: str) -> bool:
        return True
        
    def prepare_login(self, client: httpx.Client, html: str, url: str) -> dict[str, Any]:
        form = parse_login_form(html, url)
        if not form:
            raise ValueError("No login form found")
        return {"form": form}
        
    def submit_login(self, client: httpx.Client, prepared_data: dict[str, Any], username: str, password: str) -> httpx.Response:
        form = prepared_data["form"]
        data = form.inputs.copy()
        if form.user_field: data[form.user_field] = username
        if form.pass_field: data[form.pass_field] = password
            
        req = client.build_request(form.method, form.action, data=data)
        return client.send(req)
        
    def keepalive(self, client: httpx.Client, html: str, url: str) -> tuple[int | None, str | None]:
        ki = parse_keepalive(html, url)
        if ki:
            return ki.interval, ki.url
        return None, None
