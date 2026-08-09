from typing import Protocol
import httpx
from ..models import PreparedLogin, KeepaliveSpec

class PortalAdapter(Protocol):
    name: str

    def matches(self, html: str, url: str) -> bool:
        ...
        
    def prepare_login(self, client: httpx.Client, html: str, url: str) -> PreparedLogin:
        ...
        
    def submit_login(self, client: httpx.Client, prepared: PreparedLogin, username: str, password: str) -> httpx.Response:
        ...
        
    def get_keepalive(self, client: httpx.Client, html: str, url: str) -> KeepaliveSpec | None:
        ...
