# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]
### Added
- **FortinetAdapter**: Dedicated adapter for Fortinet FortiGate firewalls to handle the `magic` token natively instead of relying on generic form parsing.
- **Pre-emptive Logout**: The Fortinet adapter now executes a background GET request to the `/logout` endpoint before authenticating to clear stale MAC sessions (inspired by WiFix).
- **Explicit Keepalive**: The daemon loop now actively pings the specific `/keepalive?magic=...` URL returned by the firewall every 30 minutes, guaranteeing the session stays alive.
- **IIITK Profile Validation**: Added regex validation for the `iiitk` profile during `camp-fi creds set` to warn users against malformed student IDs (e.g., missing the correct year or branch code).

## [0.1.0] - 2026-08-03
### Added
- Initial project skeleton with `uv` and `pyproject.toml`.
- Config, paths, and OS keyring-based credential storage.
- Network probes utilizing standard endpoints (`generate_204`) to detect captive status.
- Generic HTML form parser and fallback mechanism for meta/JS redirects.
- Automated daemon loop with exponential backoff for portal login attempts.
- systemd `--user` integration for background execution.
