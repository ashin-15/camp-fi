# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.2.0] - 2026-08-09
### Added
- **Structured Login Contracts**: Added typed `LoginResult`, `LoginStatus`, and `KeepaliveSpec` models.
- **GenericFormAdapter**: Registered generic HTML form adapter as a safe fallback for unhandled captive portal forms.
- **Centralized TLS & Session Store**: Centralized HTTP client construction with TLS validation enabled by default and atomic `0600` cookie persistence (`write_private_json`).
- **Expanded Probe Specifications**: Connectivity checks now cycle through Google, Cloudflare, Apple, Microsoft, and Mozilla probes.
- **Daemon State Transitions**: Refactored daemon execution using `DaemonState` and added `SIGINT`/`SIGTERM` signal handlers.
- **Expanded Operational CLI**: Added `profile` management commands (`list`, `add`, `show`), `creds delete`, `login` one-shot command, `status`, `init` diagnostics, and `inspect-har`.
- **Hardened Systemd Integration**: Unit generation now uses `sys.executable -m camp_fi`, `wants/after network-online.target`, subprocess execution, and includes `service restart`/`service uninstall`.

### Fixed
- Fixed unpacking bug in login test where `execute_login()` returned a tuple instead of structured result.
- Fixed unsafe default `verify=False` HTTP clients and missing strict cookie permissions.
- Removed hard-coded fallback that sent non-IIITK captive portals to IIITK auth host.
## [0.1.0] - 2026-08-03
### Added
- Initial project skeleton with `uv` and `pyproject.toml`.
- Config, paths, and OS keyring-based credential storage.
- Network probes utilizing standard endpoints (`generate_204`) to detect captive status.
- Generic HTML form parser and fallback mechanism for meta/JS redirects.
- Automated daemon loop with exponential backoff for portal login attempts.
- systemd `--user` integration for background execution.
