import logging
import os
import shlex
import subprocess
import sys
from pathlib import Path

logger = logging.getLogger("camp-fi")

SERVICE_TEMPLATE = """[Unit]
Description=camp-fi Captive Portal Auto-Login Daemon
Wants=network-online.target
After=network-online.target
StartLimitIntervalSec=300
StartLimitBurst=5

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
        invoked_script = Path(sys.argv[0])
        if (
            invoked_script.name == "camp-fi"
            and invoked_script.is_absolute()
            and os.access(invoked_script, os.X_OK)
        ):
            command = [str(invoked_script), "daemon", "--foreground"]
        else:
            command = [sys.executable, "-m", "camp_fi", "daemon", "--foreground"]
        exec_cmd = shlex.join(command)
    return SERVICE_TEMPLATE.format(exec_cmd=exec_cmd)


def _verify_service_command(exec_cmd: str) -> None:
    """Reject commands that only import camp_fi from the installer's cwd."""
    result = subprocess.run(
        [*shlex.split(exec_cmd), "--help"],
        cwd=Path.home(),
        check=False,
        text=True,
        capture_output=True,
        timeout=10,
    )
    if result.returncode != 0:
        detail = result.stderr.strip() or result.stdout.strip()
        raise RuntimeError(
            "The selected camp-fi command cannot run outside the current directory. "
            "Install camp-fi into that Python environment before installing the service."
            + (f" Details: {detail}" if detail else "")
        )

def _run_systemctl(args: list[str]) -> subprocess.CompletedProcess:
    cmd = ["systemctl", "--user"] + args
    try:
        return subprocess.run(cmd, check=True, text=True, capture_output=True)
    except subprocess.CalledProcessError as e:
        logger.error("Failed systemctl command '%s': %s", " ".join(cmd), e.stderr.strip())
        raise RuntimeError(f"systemctl error: {e.stderr.strip()}") from e

def is_service_active() -> bool | None:
    """Returns True/False if determinable, None if systemctl/unit check itself failed."""
    try:
        result = subprocess.run(
            ["systemctl", "--user", "is-active", "camp-fi.service"],
            text=True, capture_output=True, check=False,
        )
        return result.stdout.strip() == "active"
    except FileNotFoundError:
        return None  # no systemd available (e.g. non-systemd distro, containers)


def is_service_enabled() -> bool | None:
    """Returns whether the user unit is enabled, or None if systemd is unavailable."""
    try:
        result = subprocess.run(
            ["systemctl", "--user", "is-enabled", "camp-fi.service"],
            text=True, capture_output=True, check=False,
        )
        return result.returncode == 0 and result.stdout.strip() == "enabled"
    except FileNotFoundError:
        return None

def install_service():
    path = get_service_path()
    content = render_service_unit()
    exec_cmd = next(line.removeprefix("ExecStart=") for line in content.splitlines() if line.startswith("ExecStart="))
    _verify_service_command(exec_cmd)
    with path.open("w", encoding="utf-8") as f:
        f.write(content)

    logger.info("Installing and starting camp-fi systemd service...")
    _run_systemctl(["daemon-reload"])
    _run_systemctl(["reset-failed", "camp-fi.service"])
    _run_systemctl(["enable", "camp-fi.service"])
    _run_systemctl(["start", "camp-fi.service"])
    logger.info("Service installed, enabled, and started at %s", path)

def start_service():
    logger.info("Starting camp-fi systemd service...")
    _run_systemctl(["start", "camp-fi.service"])
    logger.info("camp-fi systemd service started successfully.")

def stop_service():
    logger.info("Stopping camp-fi systemd service...")
    _run_systemctl(["stop", "camp-fi.service"])
    logger.info("camp-fi systemd service stopped successfully.")

def restart_service():
    logger.info("Restarting camp-fi systemd service...")
    _run_systemctl(["restart", "camp-fi.service"])
    logger.info("camp-fi systemd service restarted successfully.")

def uninstall_service():
    logger.info("Uninstalling camp-fi systemd service...")
    path = get_service_path()
    try:
        _run_systemctl(["stop", "camp-fi.service"])
    except (RuntimeError, OSError) as exc:
        logger.warning("Could not stop camp-fi service during uninstall: %s", exc)
    try:
        _run_systemctl(["disable", "camp-fi.service"])
    except (RuntimeError, OSError) as exc:
        logger.warning("Could not disable camp-fi service during uninstall: %s", exc)

    if path.exists():
        path.unlink()
        _run_systemctl(["daemon-reload"])
    logger.info("camp-fi systemd service uninstalled successfully.")
