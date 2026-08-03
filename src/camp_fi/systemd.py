import os
import sys
from pathlib import Path

SERVICE_TEMPLATE = """[Unit]
Description=Camp-fi Captive Portal Auto-Login Daemon
After=network.target

[Service]
Type=simple
ExecStart={exec_path} daemon --foreground
Restart=on-failure
RestartSec=10

[Install]
WantedBy=default.target
"""

def get_service_path() -> Path:
    d = Path.home() / ".config" / "systemd" / "user"
    d.mkdir(parents=True, exist_ok=True)
    return d / "camp-fi.service"

def install_service():
    path = get_service_path()
    exec_path = os.path.abspath(sys.argv[0])
    content = SERVICE_TEMPLATE.format(exec_path=exec_path)
    with path.open("w") as f:
        f.write(content)
    
    os.system("systemctl --user daemon-reload")
    os.system("systemctl --user enable camp-fi.service")
    os.system("systemctl --user start camp-fi.service")
    print(f"Service installed and started at {path}")

def start_service():
    os.system("systemctl --user start camp-fi.service")

def stop_service():
    os.system("systemctl --user stop camp-fi.service")
