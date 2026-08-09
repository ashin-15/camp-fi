import httpx
from .generic_form import parse_login_form
from ..keepalive import parse_keepalive
from ..models import PreparedLogin, KeepaliveSpec

class IIITKAdapter:
    name = "iiitk"

    def matches(self, html: str, url: str) -> bool:
        return "auth.iiitkottayam.ac.in" in url.lower() or "auth.iiitkottayam.ac.in" in html.lower()
        
    def prepare_login(self, client: httpx.Client, html: str, url: str) -> PreparedLogin:
        form = parse_login_form(html, url)
        if not form:
            raise ValueError("No login form found in IIITK portal page")
        return PreparedLogin(data={"form": form})
        
    def submit_login(self, client: httpx.Client, prepared: PreparedLogin, username: str, password: str) -> httpx.Response:
        form = prepared.data["form"]
        data = form.inputs.copy()
        if form.user_field:
            data[form.user_field] = username
        if form.pass_field:
            data[form.pass_field] = password
            
        req = client.build_request(form.method, form.action, data=data)
        return client.send(req)
        
    def get_keepalive(self, client: httpx.Client, html: str, url: str) -> KeepaliveSpec | None:
        ki = parse_keepalive(html, url)
        if ki:
            return KeepaliveSpec(url=ki.url, interval_seconds=ki.interval)
        return None
