# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] - 2026-08-03
### Added
- Initial project skeleton with `uv` and `pyproject.toml`.
- Config, paths, and OS keyring-based credential storage.
- Network probes utilizing standard endpoints (`generate_204`) to detect captive status.
- Generic HTML form parser and fallback mechanism for meta/JS redirects.
- Automated daemon loop with exponential backoff for portal login attempts.
- systemd `--user` integration for background execution.
