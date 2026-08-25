import re
from bs4 import BeautifulSoup
from urllib.parse import urljoin

class KeepaliveInfo:
    def __init__(self, url: str, interval: int):
        self.url = url
        self.interval = interval

JS_KEEPALIVE_RE = re.compile(
    r"setInterval\s*\(\s*function\s*\(\s*\)\s*\{[^}]*?fetch\(['\"]([^'\"]+)['\"]|"
    r"setInterval\s*\([^,]+,\s*(\d+)\s*\)",
    re.IGNORECASE | re.DOTALL,
)

def parse_js_keepalive(html: str, base_url: str) -> KeepaliveInfo | None:
    """Extract a JS setInterval-driven keepalive ping (URL + interval in ms)."""
    url_match = re.search(
        r"setInterval\([^,]*(?:fetch|XMLHttpRequest|\.open)\([^)]*['\"]([^'\"]+)['\"]",
        html,
        re.IGNORECASE | re.DOTALL,
    )
    interval_match = re.search(r"setInterval\([^,]+,\s*(\d+)\s*\)", html, re.IGNORECASE | re.DOTALL)
    if not interval_match:
        interval_match = re.search(r"setInterval\(.+?,\s*(\d+)\s*\)", html, re.IGNORECASE | re.DOTALL)
    if url_match and interval_match:
        interval_s = max(45, int(interval_match.group(1)) // 1000)
        return KeepaliveInfo(urljoin(base_url, url_match.group(1)), interval_s)
    return None

def parse_keepalive(html: str, base_url: str) -> KeepaliveInfo | None:
    """Extract keepalive URL and interval from HTML (meta refresh or JS setInterval)."""
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
                
    return parse_js_keepalive(html, base_url)
