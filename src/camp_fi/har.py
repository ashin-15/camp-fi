import json
from pathlib import Path
from pydantic import BaseModel

class HarAction(BaseModel):
    url: str
    method: str
    headers: dict[str, str]
    data: dict[str, str]

def parse_login_har(har_path: Path, username_field_hints: list[str] = None, password_field_hints: list[str] = None) -> HarAction | None:
    """Parse a HAR file to find the captive portal login request."""
    username_field_hints = username_field_hints or ["username", "user", "userid"]
    password_field_hints = password_field_hints or ["password", "pass", "pwd"]
    
    with har_path.open("r", encoding="utf-8") as f:
        har_data = json.load(f)
        
    for entry in har_data.get("log", {}).get("entries", []):
        req = entry.get("request", {})
        if req.get("method") == "POST" and "postData" in req:
            post_data = req["postData"]
            if post_data.get("mimeType", "").startswith("application/x-www-form-urlencoded"):
                params = post_data.get("params", [])
                param_dict = {p["name"]: p["value"] for p in params}
                
                has_user = any(any(h in k.lower() for h in username_field_hints) for k in param_dict)
                has_pass = any(any(h in k.lower() for h in password_field_hints) for k in param_dict)
                
                if has_user and has_pass:
                    headers = {h["name"]: h["value"] for h in req.get("headers", [])}
                    return HarAction(
                        url=req["url"],
                        method=req["method"],
                        headers=headers,
                        data=param_dict
                    )
    return None
