import os
from pathlib import Path

from platformdirs import user_config_dir, user_state_dir

APP_NAME = "camp-fi"

def get_config_dir() -> Path:
    d = Path(user_config_dir(APP_NAME))
    d.mkdir(parents=True, exist_ok=True)
    return d

def get_state_dir() -> Path:
    d = Path(user_state_dir(APP_NAME))
    d.mkdir(parents=True, exist_ok=True)
    return d

def get_config_path() -> Path:
    return get_config_dir() / "config.yaml"

def get_history_path() -> Path:
    return get_state_dir() / "history.jsonl"
def get_live_state_path() -> Path:
    return get_state_dir() / "daemon_live_state.json"


def get_cookie_path(profile: str) -> Path:
    p = get_state_dir() / f"cookies-{profile}.json"
    if p.exists():
        # Ensure 0600 permissions
        os.chmod(p, 0o600)
    return p
