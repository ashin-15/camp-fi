import os
import json
import logging
import tempfile
from pathlib import Path
from typing import Any
from dataclasses import dataclass, asdict
import httpx

logger = logging.getLogger("camp-fi")

@dataclass
class StoredCookie:
    name: str
    value: str
    domain: str | None = None
    path: str = "/"
    expires_at: int | float | None = None
    secure: bool = False
    http_only: bool = False

def write_private_json(path: Path, data: Any) -> None:
    """Write JSON data to path atomically with mode 0600."""
    parent = path.parent
    parent.mkdir(parents=True, exist_ok=True)
    try:
        os.chmod(parent, 0o700)
    except OSError:
        pass

    with tempfile.NamedTemporaryFile("w", dir=parent, delete=False, encoding="utf-8") as tmp:
        tmp_name = tmp.name
        os.chmod(tmp_name, 0o600)
        json.dump(data, tmp, indent=2)
        tmp.flush()
        os.fsync(tmp.fileno())

    os.replace(tmp_name, path)
    os.chmod(path, 0o600)

def save_cookies(client: httpx.Client, path: Path) -> None:
    """Save client cookies into an atomic 0600 file."""
    cookies_data = []
    for cookie in client.cookies.jar:
        c_dict = {
            "name": cookie.name,
            "value": cookie.value,
            "domain": cookie.domain or "",
            "path": cookie.path or "/",
            "expires_at": getattr(cookie, "expires", None),
            "secure": getattr(cookie, "secure", False),
        }
        cookies_data.append(c_dict)

    write_private_json(path, cookies_data)

def load_cookies(client: httpx.Client, path: Path, default_url: str) -> None:
    """Load cookies from private JSON file into client."""
    if not path.exists():
        return

    try:
        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)

        if isinstance(data, dict):
            # Backward compatibility with simple {name: value} format
            default_host = httpx.URL(default_url).host
            for k, v in data.items():
                client.cookies.set(k, str(v), domain=default_host)
        elif isinstance(data, list):
            for item in data:
                if isinstance(item, dict) and "name" in item and "value" in item:
                    domain = item.get("domain") or httpx.URL(default_url).host
                    path_val = item.get("path") or "/"
                    client.cookies.set(item["name"], str(item["value"]), domain=domain, path=path_val)
    except Exception as e:
        logger.warning(f"Failed to load cookies from {path} (corrupt/invalid): {e}. Discarding cookie file.")
        try:
            path.unlink(missing_ok=True)
        except OSError:
            pass
