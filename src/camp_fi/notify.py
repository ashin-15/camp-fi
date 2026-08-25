import logging
import shutil
import subprocess

logger = logging.getLogger("camp-fi")


def notify(title: str, message: str, urgency: str = "normal") -> None:
    """Best-effort desktop notification via notify-send. No-op if unavailable."""
    if not shutil.which("notify-send"):
        return
    try:
        subprocess.run(
            ["notify-send", "-u", urgency, "-a", "camp-fi", title, message],
            timeout=2,
            check=False,
        )
    except (subprocess.SubprocessError, OSError) as e:
        logger.debug(f"notify-send failed: {e}")
