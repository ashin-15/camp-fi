from bs4 import BeautifulSoup
import httpx
from ..models import PreparedLogin, KeepaliveSpec
from ..keepalive import parse_keepalive

from urllib.parse import urljoin

class FormInfo:
    def __init__(self, action: str, method: str, inputs: dict[str, str], user_field: str | None, pass_field: str | None):
        self.action = action
        self.method = method
        self.inputs = inputs
        self.user_field = user_field
        self.pass_field = pass_field

def parse_login_form(html: str, base_url: str) -> FormInfo | None:
    """Parse HTML and extract login form fields."""
    soup = BeautifulSoup(html, "html.parser")
    forms = soup.find_all("form")
    for form in forms:
        inputs = {}
        pass_field = None
        user_field = None
        
        for inp in form.find_all("input"):
            name = inp.get("name")
            if not name:
                continue
            
            val = inp.get("value", "")
            itype = inp.get("type", "text").lower()
            
            inputs[name] = val
            
            if itype == "password":
                pass_field = name
            elif itype in ("text", "email") or "user" in name.lower():
                if not user_field:
                    user_field = name
                    
        if pass_field:
            action = form.get("action", "")
            action_url = urljoin(base_url, action)
            method = form.get("method", "POST").upper()
            return FormInfo(action_url, method, inputs, user_field, pass_field)
            
    return None
class GenericFormAdapter:
    name = "generic_form"

    def matches(self, html: str, url: str) -> bool:
        return parse_login_form(html, url) is not None

    def prepare_login(self, client: httpx.Client, html: str, url: str) -> PreparedLogin:
        form = parse_login_form(html, url)
        if not form:
            raise ValueError("No login form found")
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
