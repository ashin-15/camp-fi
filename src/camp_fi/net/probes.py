import httpx
from enum import Enum, auto

class ConnectivityStatus(Enum):
    INTERNET = auto()
    CAPTIVE = auto()
    OFFLINE = auto()

class ProbeResult:
    def __init__(self, status: ConnectivityStatus, redirect_url: str | None = None, response: httpx.Response | None = None):
        self.status = status
        self.redirect_url = redirect_url
        self.response = response

    def __repr__(self):
        return f"<ProbeResult status={self.status.name} redirect_url={self.redirect_url}>"

PROBE_URLS = [
    "http://connectivitycheck.gstatic.com/generate_204",
    "http://cp.cloudflare.com/generate_204",
]

def check_connectivity(timeout: float = 3.0) -> ProbeResult:
    """Check network connectivity and classify status."""
    url = PROBE_URLS[0]
    
    with httpx.Client(timeout=timeout, follow_redirects=False) as client:
        try:
            resp = client.get(url)
            
            if resp.status_code == 204:
                return ProbeResult(ConnectivityStatus.INTERNET, response=resp)
            
            if 300 <= resp.status_code < 400 and "location" in resp.headers:
                return ProbeResult(ConnectivityStatus.CAPTIVE, redirect_url=resp.headers["location"], response=resp)
                
            if resp.status_code == 200:
                # Intercepted without redirect
                return ProbeResult(ConnectivityStatus.CAPTIVE, redirect_url=url, response=resp)
                
        except httpx.RequestError:
            return ProbeResult(ConnectivityStatus.OFFLINE)
            
    return ProbeResult(ConnectivityStatus.OFFLINE)
