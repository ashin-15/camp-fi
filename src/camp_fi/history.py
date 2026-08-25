import json
import os
import tempfile
import time
from pathlib import Path

from .models import LoginResult

MAX_HISTORY_LINES = 5000
ROTATED_HISTORY_LINES = 2000


def record_event(path: Path, event_type: str, profile: str, result: LoginResult | None = None) -> None:
    parent = path.parent
    parent.mkdir(parents=True, exist_ok=True)
    try:
        os.chmod(parent, 0o700)
    except OSError:
        pass

    _rotate_if_needed(path)

    entry = {
        "ts": time.time(),
        "event": event_type,
        "profile": profile,
        "adapter": result.adapter_name if result else None,
        "status": result.status.name if result else None,
        "message": result.message if result else None,
    }
    payload = json.dumps(entry) + "\n"
    fd = os.open(path, os.O_APPEND | os.O_CREAT | os.O_WRONLY, 0o600)
    try:
        with os.fdopen(fd, "a", encoding="utf-8") as f:
            f.write(payload)
            f.flush()
            os.fsync(f.fileno())
    finally:
        os.chmod(path, 0o600)


def read_recent(path: Path, limit: int = 20) -> list[dict]:
    if not path.exists():
        return []
    lines = path.read_text().splitlines()[-limit:]
    return [json.loads(line) for line in lines if line.strip()]


def _rotate_if_needed(path: Path) -> None:
    if not path.exists():
        return

    lines = path.read_text().splitlines()
    if len(lines) <= MAX_HISTORY_LINES:
        os.chmod(path, 0o600)
        return

    keep = lines[-ROTATED_HISTORY_LINES:]
    parent = path.parent
    with tempfile.NamedTemporaryFile("w", dir=parent, delete=False, encoding="utf-8") as tmp:
        tmp_name = tmp.name
        os.chmod(tmp_name, 0o600)
        if keep:
            tmp.write("\n".join(keep) + "\n")
        tmp.flush()
        os.fsync(tmp.fileno())

    os.replace(tmp_name, path)
    os.chmod(path, 0o600)
