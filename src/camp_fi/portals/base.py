from typing import Protocol, Any
import httpx

class PortalAdapter(Protocol):
    def matches(self, html: str, url: str) -> bool:
        ...
        
    def prepare_login(self, client: httpx.Client, html: str, url: str) -> dict[str, Any]:
        ...
        
    def submit_login(self, client: httpx.Client, prepared_data: dict[str, Any], username: str, password: str) -> httpx.Response:
        ...
        
    def keepalive(self, client: httpx.Client, html: str, url: str) -> int | None:
        ...
