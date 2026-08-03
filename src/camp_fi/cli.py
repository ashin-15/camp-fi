import typer
from .config import load_config, save_config
from .paths import get_config_path
from .credentials import set_password, delete_password
from .daemon import run_daemon
from .systemd import install_service, start_service, stop_service
from .har import parse_login_har
from pathlib import Path

app = typer.Typer(help="Wi-Fi Captive Portal Auto-Login Daemon")
config_app = typer.Typer(help="Manage configuration")
ssids_app = typer.Typer(help="Manage SSIDs for a profile")
creds_app = typer.Typer(help="Manage credentials for a profile")
systemd_app = typer.Typer(help="Manage systemd service")

app.add_typer(config_app, name="config")
config_app.add_typer(ssids_app, name="ssids")
app.add_typer(creds_app, name="creds")
app.add_typer(systemd_app, name="service")

@app.command("daemon")
def daemon(foreground: bool = typer.Option(False, "--foreground", help="Run in foreground")):
    from .logging_config import setup_logging
    setup_logging()
    run_daemon(foreground)

@app.command("capture-har")
def capture_har(har_path: Path, profile: str = typer.Option(..., help="Profile to assign")):
    action = parse_login_har(har_path)
    if action:
        typer.echo(f"Found login action: {action.url}")
    else:
        typer.echo("No login action found in HAR.")

@creds_app.command("set")
def creds_set(profile: str, username: str, password: str = typer.Option(..., prompt=True, hide_input=True)):
    set_password(profile, username, password)
    config = load_config()
    if profile in config.profiles:
        config.profiles[profile].username = username
        save_config(config)
    typer.echo(f"Credentials saved for profile '{profile}'.")

@systemd_app.command("install")
def service_install():
    install_service()

@systemd_app.command("start")
def service_start():
    start_service()

@systemd_app.command("stop")
def service_stop():
    stop_service()

@ssids_app.command("add")
def ssids_add(profile: str = typer.Option(..., help="Profile name"), ssid: str = typer.Argument(..., help="SSID to add")):
    config = load_config()
    if profile not in config.profiles:
        typer.echo(f"Profile '{profile}' not found.")
        raise typer.Exit(1)
    
    if ssid not in config.profiles[profile].ssids:
        config.profiles[profile].ssids.append(ssid)
        save_config(config)
        typer.echo(f"Added SSID '{ssid}' to profile '{profile}'.")
    else:
        typer.echo(f"SSID '{ssid}' already in profile '{profile}'.")

@ssids_app.command("remove")
def ssids_remove(profile: str = typer.Option(..., help="Profile name"), ssid: str = typer.Argument(..., help="SSID to remove")):
    config = load_config()
    if profile not in config.profiles:
        typer.echo(f"Profile '{profile}' not found.")
        raise typer.Exit(1)
    
    if ssid in config.profiles[profile].ssids:
        config.profiles[profile].ssids.remove(ssid)
        save_config(config)
        typer.echo(f"Removed SSID '{ssid}' from profile '{profile}'.")
    else:
        typer.echo(f"SSID '{ssid}' not found in profile '{profile}'.")

if __name__ == "__main__":
    app()
