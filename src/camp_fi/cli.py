from pathlib import Path

import typer

from .config import load_config, save_config
from .credentials import delete_password, set_password
from .daemon import run_daemon
from .har import parse_login_har
from .systemd import install_service, start_service, stop_service

app = typer.Typer(help="Wi-Fi Captive Portal Auto-Login Daemon")
config_app = typer.Typer(help="Manage configuration")
profile_app = typer.Typer(help="Manage profiles")
ssids_app = typer.Typer(help="Manage SSIDs for a profile")
keepalive_app = typer.Typer(help="Manage keepalive settings for a profile")
creds_app = typer.Typer(help="Manage credentials for a profile")
systemd_app = typer.Typer(help="Manage systemd service")

app.add_typer(config_app, name="config")
app.add_typer(profile_app, name="profile")
config_app.add_typer(ssids_app, name="ssids")
config_app.add_typer(keepalive_app, name="keepalive")
app.add_typer(creds_app, name="creds")
app.add_typer(systemd_app, name="service")
@app.command("daemon")
def daemon(foreground: bool = typer.Option(False, "--foreground", help="Run in foreground")):
    from .logging_config import setup_logging
    setup_logging()
    run_daemon(foreground)

@app.command("inspect-har")
def inspect_har(har_path: Path):
    action = parse_login_har(har_path)
    if action:
        typer.echo(f"Found login action URL: {action.url}")
        typer.echo(f"Method: {action.method}")
        typer.echo(f"Parameters detected: {', '.join(action.data.keys())}")
    else:
        typer.echo("No login action found in HAR.")

@profile_app.command("list")
def profile_list():
    config = load_config()
    if not config.profiles:
        typer.echo("No profiles configured.")
        return
    for name, prof in config.profiles.items():
        ssids_str = ", ".join(prof.ssids) if prof.ssids else "None"
        typer.echo(f"- {name}: user='{prof.username}', ssids=[{ssids_str}]")

@profile_app.command("add")
def profile_add(name: str):
    from .config import ProfileConfig
    config = load_config()
    if name in config.profiles:
        typer.echo(f"Profile '{name}' already exists.")
        raise typer.Exit(1)
    config.profiles[name] = ProfileConfig()
    save_config(config)
    typer.echo(f"Profile '{name}' created.")

@profile_app.command("show")
def profile_show(name: str):
    config = load_config()
    if name not in config.profiles:
        typer.echo(f"Profile '{name}' not found.")
        raise typer.Exit(1)
    prof = config.profiles[name]
    typer.echo(f"Profile: {name}")
    typer.echo(f"SSIDs: {', '.join(prof.ssids) if prof.ssids else 'None'}")
    if prof.keepalive_url:
        typer.echo(f"Keepalive URL: {prof.keepalive_url}")
    if prof.keepalive_interval_seconds is not None:
        typer.echo(f"Keepalive Interval: {prof.keepalive_interval_seconds}s")
@creds_app.command("set")
def creds_set(profile: str, username: str, password: str = typer.Option(..., prompt=True, hide_input=True)):
    import re
    if profile == "iiitk":
        if not re.match(r"^202[1-9](bc[a-z]|bec)[0-9]{4}$", username, re.IGNORECASE):
            typer.echo(f"Warning: Username '{username}' does not match standard IIITK student ID format.", err=True)
            if not typer.confirm("Do you want to continue anyway?"):
                raise typer.Exit(1)
    
    set_password(profile, username, password)
    config = load_config()
    if profile in config.profiles:
        config.profiles[profile].username = username
        save_config(config)

@creds_app.command("delete")
def creds_delete(profile: str):
    config = load_config()
    if profile in config.profiles:
        username = config.profiles[profile].username
        if username:
            delete_password(profile, username)
            config.profiles[profile].username = ""
            save_config(config)
            typer.echo(f"Credentials deleted for profile '{profile}'.")
            return
    typer.echo(f"No credentials found for profile '{profile}'.")

@systemd_app.command("install")
def service_install():
    install_service()

@systemd_app.command("start")
def service_start():
    start_service()

@systemd_app.command("stop")
def service_stop():
    stop_service()

@systemd_app.command("restart")
def service_restart():
    from .systemd import restart_service
    restart_service()

@systemd_app.command("uninstall")
def service_uninstall():
    from .systemd import uninstall_service
    uninstall_service()

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

@keepalive_app.command("set")
def keepalive_set(
    profile: str = typer.Option(..., "--profile", "-p", help="Profile name"),
    url: str | None = typer.Option(None, "--url", help="Manual keepalive URL"),
    interval: int | None = typer.Option(None, "--interval", help="Manual keepalive interval in seconds"),
):
    config = load_config()
    if profile not in config.profiles:
        typer.echo(f"Profile '{profile}' not found.", err=True)
        raise typer.Exit(1)

    prof = config.profiles[profile]
    if url is not None:
        prof.keepalive_url = url
    if interval is not None:
        prof.keepalive_interval_seconds = interval
    save_config(config)
    typer.echo(f"Keepalive settings updated for profile '{profile}'.")
@app.command("login")
def login(profile: str = typer.Option(None, help="Profile to use (defaults to active SSID match)")):
    from .credentials import get_password
    from .history import record_event
    from .net.captive import execute_login
    from .net.probes import ConnectivityStatus, check_connectivity
    from .net.ssid import get_current_ssid
    from .paths import get_cookie_path, get_history_path

    config = load_config()
    selected_profile = profile

    if not selected_profile:
        ssid = get_current_ssid()
        if ssid:
            for name, prof in config.profiles.items():
                if ssid in prof.ssids:
                    selected_profile = name
                    break

    if not selected_profile:
        typer.echo("No profile specified and no matching profile for current SSID.", err=True)
        raise typer.Exit(1)

    if selected_profile not in config.profiles:
        typer.echo(f"Profile '{selected_profile}' not found.", err=True)
        raise typer.Exit(1)

    prof = config.profiles[selected_profile]
    password = get_password(selected_profile, prof.username)
    if not password:
        typer.echo(f"No stored credentials for profile '{selected_profile}' (user '{prof.username}').", err=True)
        raise typer.Exit(1)

    probe = check_connectivity()
    if probe.status == ConnectivityStatus.INTERNET:
        typer.echo("Already connected to the Internet.")
        return
    elif probe.status != ConnectivityStatus.CAPTIVE or not probe.redirect_url:
        typer.echo(f"No captive portal detected (Status: {probe.status.name}).", err=True)
        raise typer.Exit(1)

    record_event(get_history_path(), "captive_detected", selected_profile)

    cookies_path = get_cookie_path(selected_profile)
    result = execute_login(probe.redirect_url, prof.username, password, cookies_path)
    record_event(
        get_history_path(),
        "login_success" if result.succeeded else "login_failed",
        selected_profile,
        result,
    )
    if result.succeeded:
        typer.echo(f"Login successful via adapter '{result.adapter_name}'.")
    else:
        typer.echo(f"Login failed ({result.status.name}): {result.message}", err=True)
        raise typer.Exit(1)

@app.command("history")
def history(limit: int = typer.Option(20, help="Number of recent events to show")):
    import datetime

    from .history import read_recent
    from .paths import get_history_path

    entries = read_recent(get_history_path(), limit)
    if not entries:
        typer.echo("No history recorded yet.")
        return
    for e in entries:
        ts = datetime.datetime.fromtimestamp(e["ts"], tz=datetime.timezone.utc).astimezone().strftime("%Y-%m-%d %H:%M:%S")
        typer.echo(
            f"[{ts}] {e['event']} profile={e['profile']} adapter={e.get('adapter')} "
            f"status={e.get('status')} {e.get('message') or ''}"
        )

@app.command("status")
def status():
    from .credentials import get_password
    from .net.probes import check_connectivity
    from .net.ssid import get_current_ssid
    from .paths import get_config_path, get_cookie_path

    config = load_config()
    ssid = get_current_ssid() or "Disconnected / Unknown"
    probe = check_connectivity()

    typer.echo("=== camp-fi status ===")
    typer.echo(f"Current SSID: {ssid}")
    typer.echo(f"Network Status: {probe.status.name}")
    typer.echo(f"Config File: {get_config_path()}")
    typer.echo("\nConfigured Profiles:")
    for name, prof in config.profiles.items():
        has_pass = bool(get_password(name, prof.username)) if prof.username else False
        cookie_p = get_cookie_path(name)
        cookie_info = "Present" if cookie_p.exists() else "None"
        typer.echo(f"  - {name}: user='{prof.username or 'None'}', pass_stored={has_pass}, cookies={cookie_info}")

@app.command("init")
def init():
    import shutil

    import keyring

    from .paths import get_config_dir, get_state_dir

    typer.echo("=== camp-fi initialization check ===")
    cfg_dir = get_config_dir()
    st_dir = get_state_dir()
    typer.echo(f"[OK] Config directory: {cfg_dir}")
    typer.echo(f"[OK] State directory: {st_dir}")

    has_nmcli = shutil.which("nmcli") is not None
    has_iwgetid = shutil.which("iwgetid") is not None
    if has_nmcli:
        typer.echo("[OK] Network detection: nmcli available")
    elif has_iwgetid:
        typer.echo("[OK] Network detection: iwgetid available")
    else:
        typer.echo("[WARNING] Neither nmcli nor iwgetid found in PATH. SSID detection will fail.", err=True)

    try:
        backend = keyring.get_keyring()
        typer.echo(f"[OK] Keyring backend: {backend.__class__.__name__}")
    except Exception as e:
        typer.echo(f"[WARNING] Keyring backend check failed: {e}", err=True)

    typer.echo("\nInitialization check complete.")

def _print_doctor_report(report: dict):
    import datetime

    typer.echo("=== camp-fi doctor ===\n")
    checks = report.get("checks", {})
    warnings = report.get("warnings", [])

    # --- Environment ---
    typer.echo("--- Environment ---")
    cfg_dir = checks.get("config_dir")
    st_dir = checks.get("state_dir")
    if cfg_dir:
        typer.echo(f"[OK] Config directory: {cfg_dir}")
    if st_dir:
        typer.echo(f"[OK] State directory: {st_dir}")

    ssid_tool = checks.get("ssid_detection")
    if ssid_tool:
        typer.echo(f"[OK] Network detection: {ssid_tool} available")
    else:
        typer.echo("[WARNING] Network detection: Neither nmcli nor iwgetid found in PATH.")

    backend = checks.get("keyring_backend")
    if backend and "fail" not in backend.lower() and "null" not in backend.lower():
        typer.echo(f"[OK] Keyring backend: {backend}")
    elif backend:
        typer.echo(f"[WARNING] Keyring backend: {backend} (non-functional)")
    else:
        typer.echo("[WARNING] Keyring backend: Not available")

    # --- Service ---
    typer.echo("\n--- Service ---")
    active = checks.get("systemd_service_active")
    if active is True:
        typer.echo("[OK] systemd service: active")
    elif active is False:
        typer.echo("[WARNING] systemd service: inactive (camp-fi service start)")
    else:
        typer.echo(f"[OK] systemd service: {active}")

    # --- Network ---
    typer.echo("\n--- Network ---")
    ssid = checks.get("current_ssid", "unknown")
    typer.echo(f"Current SSID: {ssid}")
    matched = checks.get("matched_profile")
    typer.echo(f"Matched Profile: {matched or 'None'}")
    conn = checks.get("connectivity_status")
    if conn:
        typer.echo(f"Connectivity: {conn}")
    if matched:
        has_pass = checks.get("credentials_stored")
        typer.echo(f"Credentials Stored: {'Yes' if has_pass else 'No'}")

    # --- Daemon State ---
    typer.echo("\n--- Daemon State ---")
    daemon_state = checks.get("daemon_state")
    if daemon_state:
        age = checks.get("daemon_state_age_seconds")
        typer.echo(f"Active Profile: {daemon_state.get('active_profile') or 'None'}")
        typer.echo(f"Last Status: {daemon_state.get('last_status') or 'None'}")
        typer.echo(
            f"Backoff: {daemon_state.get('backoff_seconds')}s "
            f"(consecutive failures: {daemon_state.get('consecutive_failures', 0)})"
        )
        if age is not None:
            typer.echo(f"State Age: {age}s ago")
    else:
        typer.echo("No live daemon state recorded.")

    # --- Recent Login Attempts ---
    typer.echo("\n--- Recent Login Attempts ---")
    recent = checks.get("recent_attempts", [])
    if recent:
        for e in recent:
            ts_val = e.get("ts")
            if ts_val:
                try:
                    ts = datetime.datetime.fromtimestamp(ts_val, tz=datetime.timezone.utc).astimezone().strftime("%Y-%m-%d %H:%M:%S")
                except Exception:
                    ts = str(ts_val)
            else:
                ts = "unknown"
            typer.echo(
                f"[{ts}] {e.get('event')} profile={e.get('profile')} "
                f"adapter={e.get('adapter')} status={e.get('status')} {e.get('message') or ''}"
            )
    else:
        typer.echo("No recent login attempts recorded.")

    # --- Summary ---
    if warnings:
        typer.echo(f"\nWarnings ({len(warnings)}):")
        for w in warnings:
            typer.echo(f"  - [WARNING] {w}")
    else:
        typer.echo("\n[OK] All checks passed.")


@app.command("doctor")
def doctor(as_json: bool = typer.Option(False, "--json", help="Output machine-readable JSON")):
    import json as _json
    import shutil
    import time

    import keyring

    from .credentials import get_password
    from .history import read_recent
    from .net.probes import check_connectivity
    from .net.ssid import get_current_ssid
    from .paths import (
        get_config_dir,
        get_config_path,
        get_history_path,
        get_live_state_path,
        get_state_dir,
    )
    from .systemd import is_service_active

    report: dict = {"checks": {}, "warnings": []}

    # --- Environment ---
    try:
        report["checks"]["config_dir"] = str(get_config_dir())
        report["checks"]["state_dir"] = str(get_state_dir())

        has_nmcli = shutil.which("nmcli") is not None
        has_iwgetid = shutil.which("iwgetid") is not None
        report["checks"]["ssid_detection"] = "nmcli" if has_nmcli else ("iwgetid" if has_iwgetid else None)
        if not (has_nmcli or has_iwgetid):
            report["warnings"].append("No nmcli or iwgetid found — SSID detection will always fail.")

        try:
            backend = keyring.get_keyring()
            report["checks"]["keyring_backend"] = backend.__class__.__name__
            if "fail" in backend.__class__.__name__.lower() or "null" in backend.__class__.__name__.lower():
                report["warnings"].append("Keyring backend appears non-functional — credentials cannot be stored.")
        except Exception as e:
            report["checks"]["keyring_backend"] = None
            report["warnings"].append(f"Keyring check failed: {e}")
    except Exception as e:
        report["warnings"].append(f"Environment check failed: {e}")

    # --- Service status ---
    try:
        active = is_service_active()
        report["checks"]["systemd_service_active"] = active
        if active is False:
            report["warnings"].append("systemd service is installed but not running (camp-fi service start).")
        elif active is None:
            report["checks"]["systemd_service_active"] = "n/a (no systemd)"
    except Exception as e:
        active = None
        report["checks"]["systemd_service_active"] = "n/a"
        report["warnings"].append(f"Service status check failed: {e}")

    # --- Current network state ---
    try:
        config = load_config()
        ssid = get_current_ssid()
        report["checks"]["current_ssid"] = ssid or "unknown"
        matched_profile = next((n for n, p in config.profiles.items() if ssid and ssid in p.ssids), None)
        report["checks"]["matched_profile"] = matched_profile
        if ssid and not matched_profile:
            report["warnings"].append(f"SSID '{ssid}' doesn't match any configured profile.")

        probe = check_connectivity()
        report["checks"]["connectivity_status"] = probe.status.name

        if matched_profile:
            prof = config.profiles[matched_profile]
            has_pass = bool(get_password(matched_profile, prof.username)) if prof.username else False
            report["checks"]["credentials_stored"] = has_pass
            if not has_pass:
                report["warnings"].append(f"No stored credentials for matched profile '{matched_profile}'.")
    except Exception as e:
        report["warnings"].append(f"Network state check failed: {e}")

    # --- Live backoff/retry state ---
    try:
        live_path = get_live_state_path()
        if live_path.exists():
            try:
                live = _json.loads(live_path.read_text())
                age = time.time() - live.get("updated_at", 0)
                report["checks"]["daemon_state"] = live
                report["checks"]["daemon_state_age_seconds"] = round(age)
                if age > 120:
                    report["warnings"].append(f"Daemon state is {round(age)}s old — daemon may be stuck or stopped.")
                if live.get("consecutive_failures", 0) >= 3:
                    report["warnings"].append(
                        f"{live['consecutive_failures']} consecutive login failures, backoff at {live.get('backoff_seconds')}s."
                    )
            except Exception:
                report["warnings"].append("Live daemon state file is corrupt.")
        else:
            report["checks"]["daemon_state"] = None
            if active:
                report["warnings"].append("Daemon is active but has not written state yet (just started?).")
    except Exception as e:
        report["warnings"].append(f"Live state check failed: {e}")

    # --- Recent history ---
    try:
        recent = read_recent(get_history_path(), limit=5)
        report["checks"]["recent_attempts"] = recent
    except Exception:
        report["checks"]["recent_attempts"] = []

    # --- Output ---
    if as_json:
        typer.echo(_json.dumps(report, indent=2, default=str))
    else:
        _print_doctor_report(report)

    if report["warnings"]:
        raise typer.Exit(1)
if __name__ == "__main__":
    app()
