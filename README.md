# camp-fi

`camp-fi` is a Python daemon designed to detect and automatically log into the IIIT Kottayam Wi-Fi captive portal (and similar generic HTML form-based captive portals). It securely stores credentials, maintains your session using keepalives, and runs quietly as a `systemd --user` service.

## How It Works

1. **SSID Detection**: The daemon continuously checks your active Wi-Fi connection using `nmcli` (or `iwgetid` as a fallback).
2. **Connectivity Probes**: If the active SSID matches a configured profile, it sends an HTTP request to standard connectivity endpoints (like `connectivitycheck.gstatic.com/generate_204`).
3. **Portal Discovery**: If the probe is redirected (HTTP 302) or intercepted, the daemon knows it's behind a captive portal.
4. **Auto-Login**: It fetches the portal page, automatically parses the HTML `<form>`, maps the username and password fields, and submits your securely stored credentials.
5. **Keepalive**: Upon successful login, it extracts any keepalive intervals (e.g., from `<meta http-equiv="refresh">`) and maintains your active session. Failed logins trigger an exponential backoff to prevent spamming the network.

## Prerequisites

- **Python 3.10+**
- **OS Keyring API**: A Secret Service implementation (e.g., GNOME Keyring, KWallet) must be running, as `camp-fi` refuses to store passwords in plaintext.
- **NetworkManager** (recommended): For `nmcli` support.

## Installation

You can install the tool using [`uv`](https://github.com/astral-sh/uv) (recommended) or `pip`:

```bash
# Clone the repository
git clone https://github.com/ashin-15/camp-fi.git
cd camp-fi

# Install globally using uv
uv tool install .
```

## Configuration

`camp-fi` uses "profiles" to manage different Wi-Fi networks and credentials. By default, it ships with an `iiitk` profile.

### 1. Configure SSIDs
Map your physical Wi-Fi SSIDs to a profile. For example, to add `IIITKottayam_5G` to the `iiitk` profile:

```bash
camp-fi config ssids add --profile iiitk IIITKottayam_5G
```
*(To remove an SSID, use `camp-fi config ssids remove --profile <profile> <ssid>`)*

### 2. Set Credentials
Set the username and password for the profile. You will be prompted to enter the password securely; it will be stored in your OS keyring.

```bash
camp-fi creds set iiitk your_student_id
```

### 3. (Optional) Advanced Config
The configuration is stored in `~/.config/camp-fi/config.yaml`. Session cookies are saved with strict permissions at `~/.local/state/camp-fi/cookies-<profile>.json`; login history is stored privately at `~/.local/state/camp-fi/history.jsonl`.

## Running the Service

### Foreground (Debugging)
To verify everything is working, run the daemon in the foreground:

```bash
camp-fi daemon --foreground
```

### Systemd Integration
Install and enable the `systemd --user` service to run the daemon automatically in the background:

```bash
# Generate the service file and start it
camp-fi service install

# You can manage the service later using:
camp-fi service stop
camp-fi service start
```

*Note: The service file is installed at `~/.config/systemd/user/camp-fi.service`.*

## CLI Reference

### Operational & Diagnostics
- `camp-fi init`: Run system initialization and environment capability checks.
- `camp-fi status`: View current SSID, network status, configuration path, and active profile status.
- `camp-fi history [--limit <n>]`: Show recent captive portal and login events.
- `camp-fi login [--profile <name>]`: Perform a one-shot captive portal authentication attempt.
- `camp-fi daemon [--foreground]`: Run the main event loop.
- `camp-fi inspect-har <har_path>`: Inspect a browser HAR export for login form patterns.

### Profiles & Credentials
- `camp-fi profile list`: List all configured profiles.
- `camp-fi profile add <name>`: Create a new profile.
- `camp-fi profile show <name>`: Display details for a specific profile.
- `camp-fi creds set <profile> <username>`: Securely store credentials in OS keyring for a profile.
- `camp-fi creds delete <profile>`: Delete stored credentials for a profile.

### SSID Configuration
- `camp-fi config ssids add --profile <profile> <ssid>`: Add an SSID to a profile.
- `camp-fi config ssids remove --profile <profile> <ssid>`: Remove an SSID from a profile.

### Service Management
- `camp-fi service install`: Generate, enable, and start the systemd `--user` unit.
- `camp-fi service start`: Start the installed systemd unit.
- `camp-fi service stop`: Stop the systemd unit.
- `camp-fi service restart`: Restart the systemd unit.
- `camp-fi service uninstall`: Disable, stop, and remove the installed systemd unit.

## Development
To hack on `camp-fi`, set up your virtual environment and run the test suite:

```bash
# Setup via uv
uv venv
source .venv/bin/activate
uv pip install -e ".[dev]"

# Run tests
uv run pytest
```
