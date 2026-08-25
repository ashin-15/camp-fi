import os
import sys
import subprocess
import logging
from pathlib import Path

logger = logging.getLogger("camp-fi")

SERVICE_TEMPLATE = """[Unit]
Description=camp-fi Captive Portal Auto-Login Daemon
Wants=network-online.target
After=network-online.target

[Service]
Type=simple
ExecStart={exec_cmd}
Restart=on-failure
RestartSec=15
TimeoutStopSec=20

[Install]
WantedBy=default.target
"""

def get_service_path() -> Path:
    d = Path.home() / ".config" / "systemd" / "user"
    d.mkdir(parents=True, exist_ok=True)
    return d / "camp-fi.service"

def render_service_unit(exec_cmd: str | None = None) -> str:
    if not exec_cmd:
        exec_cmd = f"{sys.executable} -m camp_fi daemon --foreground"
    return SERVICE_TEMPLATE.format(exec_cmd=exec_cmd)

def _run_systemctl(args: list[str]) -> subprocess.CompletedProcess:
    cmd = ["systemctl", "--user"] + args
    try:
        return subprocess.run(cmd, check=True, text=True, capture_output=True)
    except subprocess.CalledProcessError as e:
        logger.error("Failed systemctl command '%s': %s", " ".join(cmd), e.stderr.strip())
        raise RuntimeError(f"systemctl error: {e.stderr.strip()}") from e

def install_service():
    path = get_service_path()
    content = render_service_unit()
    with path.open("w", encoding="utf-8") as f:
        f.write(content)

    _run_systemctl(["daemon-reload"])
    _run_systemctl(["enable", "camp-fi.service"])
    _run_systemctl(["start", "camp-fi.service"])
    logger.info("Service installed and started at %s", path)

def start_service():
    _run_systemctl(["start", "camp-fi.service"])

def stop_service():
    _run_systemctl(["stop", "camp-fi.service"])

def restart_service():
    _run_systemctl(["restart", "camp-fi.service"])

def uninstall_service():
    path = get_service_path()
    try:
        _run_systemctl(["stop", "camp-fi.service"])
    except Exception:
        pass
    try:
        _run_systemctl(["disable", "camp-fi.service"])
    except Exception:
        pass

    if path.exists():
        path.unlink()
        _run_systemctl(["daemon-reload"])
    logger.info("Service uninstalled.")
