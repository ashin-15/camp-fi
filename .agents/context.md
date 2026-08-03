# camp-fi AI Context & Rules

## Project Overview
`camp-fi` is a Python-based background daemon that automatically detects captive portal interceptions (specifically Fortinet FortiGate firewalls like those at IIIT Kottayam) and logs the user in automatically using securely stored credentials.

## Core Architecture
- `src/camp_fi/cli.py`: The `typer` CLI entrypoint. Handles configuration, credential storage, and daemon startup.
- `src/camp_fi/daemon.py`: The main state machine. It loops, checks the active SSID (`net/ssid.py`), probes for connectivity (`net/probes.py`), and triggers the login flow.
- `src/camp_fi/net/captive.py`: Orchestrates the login execution. It automatically follows non-standard HTTP 200 OK HTML/JS redirects before delegating to a portal adapter.
- `src/camp_fi/portals/`: Contains captive portal adapters.
  - `base.py`: The `PortalAdapter` protocol (defines `matches`, `prepare_login`, `submit_login`, `keepalive`).
  - `fortinet.py`: Native support for Fortinet firewalls (extracts `magic` tokens, handles pre-emptive logouts, and extracts keepalive URLs).
- `src/camp_fi/credentials.py`: Wrapper around the OS `keyring` for secure secret storage.

## Development Rules & Conventions
1. **Package Manager**: You MUST use `uv` for package management and script execution (e.g., `uv run pytest`).
2. **Secrets Storage**: NEVER store passwords in plaintext configuration files. Always use the `keyring` API via `src/camp_fi/credentials.py`.
3. **Portal Interceptions**: Captive portals often intercept `http://connectivitycheck.gstatic.com/generate_204` by returning a `200 OK` with HTML/JS redirects (instead of a `302 Found`). Do not assume `302` is the only captive state.
4. **Adapter Protocol**: Any new captive portal integrations MUST implement the full `PortalAdapter` protocol in `portals/base.py`.
5. **Safe Logging**: The `RedactingFormatter` in `logging_config.py` attempts to scrub tokens, but you MUST avoid explicitly logging passwords or raw session tokens in newly added log statements.
6. **Changelog**: All notable user-facing changes must be documented in `CHANGELOG.md` following the [Keep a Changelog](https://keepachangelog.com/) format.
