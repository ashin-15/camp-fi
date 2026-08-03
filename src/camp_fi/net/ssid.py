import subprocess
import shutil

def get_current_ssid() -> str | None:
    """Get the currently connected Wi-Fi SSID."""
    if shutil.which("nmcli"):
        try:
            result = subprocess.run(
                ["nmcli", "-t", "-f", "active,ssid", "dev", "wifi"],
                capture_output=True, text=True, check=True
            )
            for line in result.stdout.splitlines():
                if line.startswith("yes:"):
                    return line.split(":", 1)[1].strip()
        except subprocess.SubprocessError:
            pass
            
    if shutil.which("iwgetid"):
        try:
            result = subprocess.run(
                ["iwgetid", "-r"],
                capture_output=True, text=True, check=True
            )
            ssid = result.stdout.strip()
            if ssid:
                return ssid
        except subprocess.SubprocessError:
            pass

    return None
