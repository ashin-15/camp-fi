import re
from bs4 import BeautifulSoup
from urllib.parse import urljoin

class KeepaliveInfo:
    def __init__(self, url: str, interval: int):
        self.url = url
        self.interval = interval

def parse_keepalive(html: str, base_url: str) -> KeepaliveInfo | None:
    """Extract keepalive URL and interval from HTML (meta refresh)."""
    soup = BeautifulSoup(html, "html.parser")
    meta = soup.find("meta", attrs={"http-equiv": lambda x: x and x.lower() == "refresh"})
    if meta:
        content = meta.get("content", "")
        m = re.match(r"(\d+)(?:\s*;\s*url=(.*))?", content, re.IGNORECASE)
        if m:
            interval = int(m.group(1))
            url = m.group(2)
            if url:
                url = url.strip("'\" ")
                # Default safety boundary of 45 seconds
                return KeepaliveInfo(urljoin(base_url, url), max(45, interval))
                
    # Fallback to 30 mins (1800s) if keepalive required but not stated?
    # We'll just return None here and let the caller decide
    return None
