from camp_fi.systemd import render_service_unit

def test_render_service_unit():
    unit = render_service_unit("/usr/bin/python3 -m camp_fi daemon --foreground")
    assert "ExecStart=/usr/bin/python3 -m camp_fi daemon --foreground" in unit
    assert "Wants=network-online.target" in unit
    assert "After=network-online.target" in unit
    assert "Restart=on-failure" in unit
    assert "RestartSec=15" in unit

from unittest.mock import patch
import subprocess
from camp_fi.systemd import is_service_active

def test_is_service_active_true():
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = subprocess.CompletedProcess(args=[], returncode=0, stdout="active\n", stderr="")
        assert is_service_active() is True

def test_is_service_active_false():
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = subprocess.CompletedProcess(args=[], returncode=3, stdout="inactive\n", stderr="")
        assert is_service_active() is False

def test_is_service_active_file_not_found():
    with patch("subprocess.run", side_effect=FileNotFoundError("systemctl not found")):
        assert is_service_active() is None
