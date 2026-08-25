import subprocess
from unittest.mock import patch

from camp_fi.notify import notify


def test_notify_noop_when_notify_send_missing():
    with patch("shutil.which", return_value=None), patch("subprocess.run") as mock_run:
        notify("camp-fi", "Test message")
        mock_run.assert_not_called()


def test_notify_calls_subprocess_default_urgency():
    with patch("shutil.which", return_value="/usr/bin/notify-send"), patch("subprocess.run") as mock_run:
        notify("camp-fi", "Reconnected via iiitk")
        mock_run.assert_called_once_with(
            ["notify-send", "-u", "normal", "-a", "camp-fi", "camp-fi", "Reconnected via iiitk"],
            timeout=2,
            check=False,
        )


def test_notify_calls_subprocess_custom_urgency():
    with patch("shutil.which", return_value="/usr/bin/notify-send"), patch("subprocess.run") as mock_run:
        notify("camp-fi: login failing", "Invalid password", urgency="critical")
        mock_run.assert_called_once_with(
            ["notify-send", "-u", "critical", "-a", "camp-fi", "camp-fi: login failing", "Invalid password"],
            timeout=2,
            check=False,
        )


def test_notify_handles_subprocess_error_gracefully():
    with patch("shutil.which", return_value="/usr/bin/notify-send"), patch(
        "subprocess.run", side_effect=subprocess.SubprocessError("Mock error")
    ) as mock_run:
        notify("camp-fi", "Test")
        mock_run.assert_called_once()


def test_notify_handles_os_error_gracefully():
    with patch("shutil.which", return_value="/usr/bin/notify-send"), patch(
        "subprocess.run", side_effect=OSError("Mock OS error")
    ) as mock_run:
        notify("camp-fi", "Test")
        mock_run.assert_called_once()
