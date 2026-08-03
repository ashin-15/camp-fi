# IIIT Kottayam Captive Portal Auth Service Implementation Plan

> **For Hermes:** Use subagent-driven-development skill to implement this plan task-by-task.

**Goal:** Build a legitimate personal auto-login and keepalive client for IIIT Kottayam's Wi-Fi captive portal, using only the user's own authorized credentials and normal portal requests.

**Architecture:** A small Python daemon detects captive-portal state using standard connectivity probes, discovers the login/keepalive request shape from the actual portal HTML/network flow, submits credentials through a portal-specific plugin, then maintains the session with controlled keepalive refreshes. The first version should be IIITK-specific but use a plugin boundary so other portals can be added without rewriting the daemon.

**Tech Stack:** Python 3.11+, `httpx` or `requests`, `beautifulsoup4`, `pydantic-settings` or `pyyaml`, `keyring`, `platformdirs`, `systemd --user` on Linux, optional desktop notifications via `notify-send`.

---

## 0. Scope, Safety, and Non-Goals

This project is allowed only for convenience automation of the operator's own Wi-Fi login.

### Allowed

- Detect whether the current network is captive.
- Submit the same username/password the user would manually enter.
- Preserve cookies/session state locally for that account.
- Repeat the portal's normal keepalive/refresh request at a polite interval.
- Log useful diagnostics without leaking credentials.

### Not Allowed

- Bypassing authentication.
- Sharing credentials.
- MAC spoofing to impersonate another authenticated device.
- Attacking the portal, rate-limiting bypass, brute forcing, vulnerability scanning, or interfering with campus infrastructure.
- Circumventing device limits, bandwidth controls, or administrative policy.

### Policy Check

Before deployment, confirm that IIIT Kottayam's acceptable-use/network policy does not forbid personal login automation. If it is unclear, keep the service conservative:

- no parallel login attempts;
- retry backoff;
- human-visible logs;
- one account/profile only by default;
- no hidden persistence beyond a standard user-level service.

---

## 1. Research Findings to Encode into the Design

### 1.1 Captive portal behavior

Captive portals commonly block general Internet access until an HTTP login/terms page is completed. Typical mechanisms include:

- HTTP redirect from arbitrary HTTP traffic to the portal;
- DNS interception for probe domains;
- gateway-side allow/deny based on authenticated client state;
- session cookies or gateway-side session keyed to IP/MAC;
- a keepalive page using meta refresh, JavaScript timers, AJAX, hidden iframes, or periodic HTTP GET/POST.

### 1.2 Standard connectivity probes

Use multiple known HTTP endpoints because different networks intercept different probes:

| Platform | Probe URL | Expected open-Internet response |
|---|---|---|
| Android/Chrome | `http://connectivitycheck.gstatic.com/generate_204` | HTTP 204, empty body |
| Apple | `http://captive.apple.com/hotspot-detect.html` | HTTP 200 containing `Success` |
| Windows | `http://www.msftconnecttest.com/connecttest.txt` | HTTP 200 containing `Microsoft Connect Test` |
| Mozilla | `http://detectportal.firefox.com/success.txt` | HTTP 200 containing `success` |

If these return a 30x redirect, HTML login page, unexpected status, portal host, or DNS-mapped private address, assume captive portal.

### 1.3 Prior art

Existing projects like `HotspotAutoLogin` use profile-based configs containing:

- SSID/network name;
- login URL;
- payload template;
- headers;
- check interval;
- separate profiles for different Wi-Fi/Ethernet networks.

Borrow this profile model, but improve security by keeping the password out of config and using OS keyring.

### 1.4 Credential storage

Python `keyring` supports OS-native secure stores:

- Windows Credential Manager;
- macOS Keychain;
- Linux Secret Service / GNOME Keyring / KWallet.

On Linux headless/minimal setups, Secret Service may not be available. The tool must detect this and fail closed with a clear message, not fall back to plaintext unless the user explicitly enables an insecure dev-only mode.

---

## 2. Product Requirements

### 2.1 MVP User Experience

```bash
wifi-auth init
wifi-auth creds set --profile iiitk --username <roll_or_email>
wifi-auth capture --profile iiitk
wifi-auth login --profile iiitk
wifi-auth status
wifi-auth service install --user
wifi-auth service start
```

Expected behavior:

1. User connects to IIITK Wi-Fi.
2. Service detects captive portal.
3. Service submits credentials.
4. Service records session cookies and detected keepalive URL/request.
5. Service periodically checks connectivity.
6. If Internet is available, it does nothing.
7. If session expires, it logs in again.
8. If keepalive is known and session is active, it refreshes session politely.

### 2.2 MVP Functional Requirements

- FR1: Detect current SSID on Linux.
- FR2: Detect open Internet vs captive portal using HTTP probe endpoints.
- FR3: Follow captive redirect only far enough to identify login page.
- FR4: Fetch login page and parse forms/hidden inputs.
- FR5: Support a portal-specific IIITK login adapter.
- FR6: Store username/password in OS keyring.
- FR7: Store non-secret config in YAML/TOML under user config directory.
- FR8: Store cookies in a user-private state file with mode `0600`.
- FR9: Support keepalive by replaying discovered GET/POST refresh request.
- FR10: Provide CLI commands for setup, manual login, status, logs, and service install.
- FR11: Provide a Linux `systemd --user` service and timer/daemon mode.
- FR12: Redact secrets from logs.
- FR13: Retry with exponential backoff and max attempt limits.

### 2.3 Non-Functional Requirements

- Conservative request rate: default check every 30-60 seconds, login retry backoff from 15s to 10m.
- No plaintext password in config, logs, stack traces, or crash reports.
- Usable without root for the normal daemon path.
- Works offline gracefully.
- Easy debug mode that prints sanitized request/response summaries.
- Tests use local fake portal server, not live campus infrastructure.

---

## 3. Proposed Repository Layout

```text
wifi-auth-service/
  pyproject.toml
  README.md
  LICENSE
  .gitignore

  src/wifi_auth/
    __init__.py
    __main__.py
    cli.py

    config.py
    models.py
    logging_config.py
    paths.py

    net/
      __init__.py
      ssid.py
      probes.py
      captive.py
      http_client.py

    credentials.py
    session_store.py

    portals/
      __init__.py
      base.py
      generic_form.py
      iiitk.py

    keepalive.py
    daemon.py
    systemd.py

  tests/
    test_probes.py
    test_form_parser.py
    test_credentials.py
    test_session_store.py
    test_keepalive_parser.py
    test_iiitk_adapter.py
    fake_portal.py

  packaging/
    systemd/
      wifi-auth.service.template
```

---

## 4. Configuration Design

### 4.1 Non-secret config file

Path:

```text
~/.config/wifi-auth/config.yaml
```

Example:

```yaml
version: 1
active_profile: iiitk

profiles:
  iiitk:
    ssids:
      - IIITK-WiFi
      - IIITK-Student
    portal: iiitk
    username_key: iiitk
    check_interval_seconds: 45
    login_backoff:
      min_seconds: 15
      max_seconds: 600
    probes:
      - http://connectivitycheck.gstatic.com/generate_204
      - http://captive.apple.com/hotspot-detect.html
      - http://www.msftconnecttest.com/connecttest.txt
    login:
      # Filled by capture/manual setup, not guessed.
      login_url: null
      method: POST
      username_field: null
      password_field: null
      extra_fields: {}
    keepalive:
      enabled: true
      url: null
      method: GET
      interval_seconds: null
      headers: {}
      body: null
```

### 4.2 Secret storage

Use keyring service name:

```text
wifi-auth-service
```

Keyring username format:

```text
<profile>:<username>
```

CLI:

```bash
wifi-auth creds set --profile iiitk --username 2023xxxx
wifi-auth creds get --profile iiitk --username 2023xxxx  # prints only availability, never password by default
wifi-auth creds delete --profile iiitk --username 2023xxxx
```

### 4.3 State files

```text
~/.local/state/wifi-auth/
  cookies-iiitk.json       # mode 0600
  last-status.json         # sanitized
  wifi-auth.log            # sanitized
```

---

## 5. Portal Discovery/Capture Workflow

The biggest unknown is the exact IIITK portal request shape. Do not hardcode guesses. Build a capture assistant.

### 5.1 Manual browser capture path

User opens DevTools → Network, logs in once, exports HAR.

Command:

```bash
wifi-auth capture-har --profile iiitk ~/Downloads/iiitk-login.har
```

The tool should:

1. Parse HAR entries.
2. Find candidate login POSTs with username/password field names.
3. Extract:
   - request URL;
   - method;
   - content type;
   - relevant headers;
   - form/body keys with password redacted;
   - hidden tokens;
   - post-login redirect URL;
   - keepalive page URL(s).
4. Ask the user to confirm the chosen request.
5. Save non-secret shape to config.

### 5.2 Direct HTML capture path

Command:

```bash
wifi-auth capture --profile iiitk
```

The tool should:

1. Run connectivity probes.
2. Detect redirect location.
3. Fetch login page.
4. Parse forms with BeautifulSoup.
5. Score candidate forms:
   - has password input: +5;
   - has username-like input: +3;
   - action contains login/auth: +2;
   - method POST: +2;
   - contains hidden token fields: +1.
6. Print sanitized summary.
7. Save selected form metadata.

### 5.3 Why HAR support matters

Some portals use JavaScript-generated requests, CSRF tokens, dynamic challenge values, or AJAX login endpoints that static form parsing will miss. HAR import gives the user a reliable no-guessing path.

---

## 6. Core State Machine

```text
START
  │
  ▼
Load config + credentials
  │
  ▼
Detect SSID/network
  │
  ├── not matching configured profile ──► sleep longer
  │
  ▼
Run connectivity probes
  │
  ├── internet OK ──► maybe keepalive if due ──► sleep
  │
  ├── DNS/offline/network down ──► sleep/backoff
  │
  └── captive portal detected
         │
         ▼
      Resolve portal adapter
         │
         ▼
      Fetch login page / token
         │
         ▼
      Submit login once
         │
         ├── success ──► save cookies/session ──► discover keepalive ──► sleep
         ├── invalid creds ──► notify + stop retrying until user action
         └── transient fail ──► exponential backoff
```

---

## 7. Module-Level Design

### 7.1 `net/probes.py`

Responsibilities:

- Perform HTTP GET to each probe URL.
- Use short timeouts: connect 3s, read 5s.
- Disable automatic redirect for initial classification.
- Return structured results.

Model:

```python
class ProbeResult(BaseModel):
    url: str
    status_code: int | None
    final_url: str | None
    location: str | None
    body_sample: str | None
    error: str | None
    verdict: Literal["internet", "captive", "offline", "unknown"]
```

Classification rules:

- `generate_204` returns 204 → internet.
- Apple endpoint returns 200 and contains `Success` → internet.
- Windows endpoint returns expected body → internet.
- 30x redirect to non-expected host → captive.
- 200 HTML with form/password/portal branding → captive.
- DNS failure/timeout for all probes → offline or DNS captive, needs secondary check.

### 7.2 `net/ssid.py`

Linux implementations in priority order:

1. `nmcli -t -f active,ssid dev wifi | awk -F: '$1=="yes" {print $2}'` equivalent via Python subprocess, not shell parsing if possible.
2. `iwgetid -r` fallback.
3. Return `None` if unavailable.

Do not require root.

### 7.3 `credentials.py`

Responsibilities:

- Wrap `keyring`.
- Detect unusable backend.
- Store/retrieve/delete password.
- Never log the password.

Failure handling:

- If keyring unavailable, show precise setup guidance:
  - install/unlock GNOME Keyring or KWallet;
  - run inside a desktop session;
  - optionally set explicit env vars for Secret Service.
- Do not silently write plaintext.

### 7.4 `portals/base.py`

Define adapter interface:

```python
class PortalAdapter(Protocol):
    name: str

    def matches(self, page: PortalPage, probe: CaptiveDetection) -> bool: ...
    def prepare_login(self, client: HttpClient, config: ProfileConfig) -> LoginRequest: ...
    def submit_login(self, client: HttpClient, request: LoginRequest) -> LoginResult: ...
    def discover_keepalive(self, client: HttpClient, login_result: LoginResult) -> KeepaliveConfig | None: ...
    def keepalive(self, client: HttpClient, keepalive_config: KeepaliveConfig) -> KeepaliveResult: ...
```

### 7.5 `portals/generic_form.py`

A fallback adapter for ordinary HTML forms:

- parse `<form>`;
- fill username/password fields;
- preserve hidden fields;
- submit action URL with session cookies;
- infer success by:
  - no password field in response;
  - redirect to keepalive/status page;
  - connectivity probes pass after login.

### 7.6 `portals/iiitk.py`

IIITK-specific adapter, initially a thin wrapper around captured config.

It should support custom fingerprints once real portal data is available:

- title text;
- form field names;
- keepalive page phrase like `Authentication Refresh in ... seconds`;
- specific portal host/IP;
- session cookie names if observed.

Do not guess these values from memory. Populate them from capture.

### 7.7 `keepalive.py`

Responsibilities:

- Parse keepalive page.
- Identify refresh mechanisms:
  - `<meta http-equiv="refresh" content="N;url=...">`;
  - JavaScript `setTimeout`/`setInterval` with URL fetch/location reload;
  - AJAX calls via obvious `fetch`, `XMLHttpRequest`, or jQuery `$.ajax`;
  - hidden iframe source;
  - simple page reload.
- Store sanitized keepalive config.
- Execute keepalive no more frequently than needed.

If screenshot says `Authentication Refresh in 10789 seconds`, do not refresh every 30 seconds. The connectivity checker can run every 45s, but keepalive should follow the portal's indicated timer with safety margin, e.g. refresh at 80-90% of expiry or minimum every 30 minutes if unknown.

### 7.8 `daemon.py`

Responsibilities:

- Main loop.
- Backoff.
- Signal handling.
- Status file updates.
- Optional `sd_notify` support for systemd watchdog.

Pseudocode:

```python
while not shutting_down:
    profile = choose_profile_by_ssid(config)
    if not profile:
        status("idle", "no matching SSID")
        sleep(120)
        continue

    detection = detector.check(profile.probes)

    if detection.internet_ok:
        if keepalive_due(profile):
            run_keepalive(profile)
        reset_login_backoff()
        sleep(profile.check_interval_seconds)
        continue

    if detection.offline:
        status("offline", detection.reason)
        sleep(backoff.next())
        continue

    if detection.captive:
        result = login_once(profile, detection)
        if result.success:
            save_session(result)
            notify_success_once()
            reset_login_backoff()
        elif result.invalid_credentials:
            notify_failure("invalid credentials; stopping retries")
            sleep_until_config_change_or_manual_command()
        else:
            notify_debug("login transient failure")
            sleep(backoff.next())
```

---

## 8. CLI Commands

Use `typer` or `argparse`. Prefer `typer` for UX if dependency budget is acceptable; otherwise `argparse` for stdlib-only CLI.

### Commands

```bash
wifi-auth init
wifi-auth profiles list
wifi-auth profiles show iiitk
wifi-auth profiles set-active iiitk

wifi-auth creds set --profile iiitk --username USER
wifi-auth creds check --profile iiitk
wifi-auth creds delete --profile iiitk

wifi-auth detect
wifi-auth capture --profile iiitk
wifi-auth capture-har --profile iiitk login.har
wifi-auth login --profile iiitk --debug
wifi-auth keepalive --profile iiitk
wifi-auth status

wifi-auth daemon --foreground
wifi-auth service install --user
wifi-auth service start
wifi-auth service stop
wifi-auth service status
wifi-auth service logs
```

### Debug output requirements

Debug mode may show:

- URLs;
- status codes;
- redirect locations;
- form field names;
- first 200 chars of sanitized HTML title/body;
- cookie names only, not values.

Debug mode must not show:

- password;
- full cookie values;
- auth tokens unless explicitly requested with a dangerous `--dump-sensitive` flag that defaults false.

---

## 9. systemd User Service Design

Template path:

```text
packaging/systemd/wifi-auth.service.template
```

Content:

```ini
[Unit]
Description=Wi-Fi Captive Portal Auto Login Service
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
ExecStart={venv_python} -m wifi_auth daemon --foreground
Restart=on-failure
RestartSec=15
Environment=PYTHONUNBUFFERED=1

# Hardening: user service, no root needed.
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=read-only
ReadWritePaths=%h/.config/wifi-auth %h/.local/state/wifi-auth %h/.cache/wifi-auth

[Install]
WantedBy=default.target
```

Install command should render this into:

```text
~/.config/systemd/user/wifi-auth.service
```

Then run:

```bash
systemctl --user daemon-reload
systemctl --user enable wifi-auth.service
systemctl --user start wifi-auth.service
```

Optional watchdog version can come later with `Type=notify` and `WATCHDOG=1`, but keep MVP simple.

---

## 10. Testing Strategy

Never test repeated login attempts against live IIITK infrastructure during development. Use a fake local portal.

### 10.1 Unit tests

- Probe classification:
  - 204 expected response = internet;
  - 302 to portal = captive;
  - 200 login form = captive;
  - timeout = offline/unknown.
- Form parser:
  - detects username/password fields;
  - preserves hidden fields;
  - resolves relative action URL.
- Credential wrapper:
  - mock keyring backend;
  - unavailable backend fails closed.
- Session store:
  - writes mode `0600`;
  - redacts cookie values in status output.
- Keepalive parser:
  - meta refresh;
  - JavaScript timer;
  - iframe;
  - page reload fallback.

### 10.2 Fake portal integration tests

Create `tests/fake_portal.py` with routes:

```text
/generate_204               -> if unauthenticated, 302 /login; else 204
/login GET                  -> HTML form with csrf token
/login POST                 -> validates credentials, sets cookie, redirects /keepalive
/keepalive GET              -> page containing "Authentication Refresh in 120 seconds"
/internet                   -> protected content
```

Test flow:

1. Start fake portal in pytest fixture.
2. Configure profile to use fake probe/login URLs.
3. Run login command against fake portal.
4. Verify cookie stored.
5. Verify second probe returns internet.
6. Verify keepalive request extends fake session.

### 10.3 Manual campus validation checklist

Only after local tests pass:

1. Connect to IIITK Wi-Fi.
2. Run `wifi-auth detect --debug` once.
3. Confirm it reports captive portal and shows sanitized redirect URL.
4. Run `wifi-auth capture --profile iiitk --debug`.
5. If capture fails, login manually and export HAR, then run `capture-har`.
6. Run `wifi-auth login --profile iiitk --debug` once.
7. Confirm normal Internet access using probes.
8. Leave daemon running for one expiry cycle.
9. Verify no repeated login storm in logs.

---

## 11. Implementation Tasks

### Task 1: Create Python project skeleton

**Objective:** Establish package layout and tooling.

**Files:**
- Create: `pyproject.toml`
- Create: `src/wifi_auth/__init__.py`
- Create: `src/wifi_auth/__main__.py`
- Create: `src/wifi_auth/cli.py`
- Create: `tests/`

**Steps:**

1. Create package directories.
2. Add dependencies:
   - `httpx`
   - `beautifulsoup4`
   - `pydantic`
   - `pyyaml`
   - `keyring`
   - `platformdirs`
   - `pytest`
   - `respx` or local HTTP test server support.
3. Add CLI entry point `wifi-auth = wifi_auth.cli:main`.
4. Verify:

```bash
uv sync
uv run wifi-auth --help
uv run pytest
```

Expected: CLI help prints; tests initially pass or report no tests depending setup.

### Task 2: Add config/path models

**Objective:** Support typed config and platform-correct paths.

**Files:**
- Create: `src/wifi_auth/paths.py`
- Create: `src/wifi_auth/models.py`
- Create: `src/wifi_auth/config.py`
- Test: `tests/test_config.py`

**Steps:**

1. Define config/state/cache paths with `platformdirs`.
2. Define Pydantic models for profile, login, keepalive, backoff.
3. Implement load/save YAML.
4. Write tests for default config creation and round-trip serialization.

### Task 3: Implement safe logging/redaction

**Objective:** Prevent accidental credential leakage.

**Files:**
- Create: `src/wifi_auth/logging_config.py`
- Test: `tests/test_redaction.py`

**Steps:**

1. Implement `redact_mapping()` for keys containing `password`, `token`, `cookie`, `secret`, `auth`.
2. Implement URL redaction for query params with sensitive names.
3. Add tests with representative request/response samples.

### Task 4: Implement connectivity probes

**Objective:** Classify Internet/captive/offline state.

**Files:**
- Create: `src/wifi_auth/net/http_client.py`
- Create: `src/wifi_auth/net/probes.py`
- Test: `tests/test_probes.py`

**Steps:**

1. Add `httpx.Client` wrapper with timeouts and browser-like User-Agent.
2. Implement probe execution with redirects disabled.
3. Implement expected-response classification table.
4. Add tests for 204, Apple Success, Microsoft text, redirect, login HTML, timeout.

### Task 5: Implement SSID detection

**Objective:** Choose profile based on current Wi-Fi network.

**Files:**
- Create: `src/wifi_auth/net/ssid.py`
- Test: `tests/test_ssid.py`

**Steps:**

1. Implement `nmcli` parser.
2. Implement `iwgetid -r` fallback.
3. Mock subprocess in tests.
4. Ensure missing tools return `None`, not crash.

### Task 6: Implement credential storage

**Objective:** Store password securely through OS keyring.

**Files:**
- Create: `src/wifi_auth/credentials.py`
- Test: `tests/test_credentials.py`

**Steps:**

1. Wrap keyring set/get/delete.
2. Detect unusable/fail backends.
3. Implement CLI `creds set/check/delete`.
4. Tests use a fake in-memory keyring backend.

### Task 7: Implement session cookie store

**Objective:** Persist cookies safely between daemon iterations.

**Files:**
- Create: `src/wifi_auth/session_store.py`
- Test: `tests/test_session_store.py`

**Steps:**

1. Serialize cookies from `httpx`/`requests` client.
2. Save to state path with file mode `0600`.
3. Load into new client session.
4. Redact cookie values in status output.

### Task 8: Implement generic form parser

**Objective:** Extract login form metadata from portal HTML.

**Files:**
- Create: `src/wifi_auth/portals/base.py`
- Create: `src/wifi_auth/portals/generic_form.py`
- Test: `tests/test_form_parser.py`

**Steps:**

1. Parse forms with BeautifulSoup.
2. Score candidate forms.
3. Identify username/password fields.
4. Preserve hidden fields.
5. Resolve relative action URL against page URL.
6. Add tests for common form variants.

### Task 9: Implement IIITK adapter wrapper

**Objective:** Add a portal-specific adapter that uses captured config and future IIITK fingerprints.

**Files:**
- Create: `src/wifi_auth/portals/iiitk.py`
- Test: `tests/test_iiitk_adapter.py`

**Steps:**

1. Implement `matches()` using configured host/title/form fingerprints.
2. Delegate form mechanics to generic adapter initially.
3. Add extension points for custom hidden fields/tokens.
4. Add tests using synthetic IIITK-like HTML from screenshots, without guessing private URLs.

### Task 10: Implement HAR capture importer

**Objective:** Let the user derive exact login request shape from browser DevTools export.

**Files:**
- Create: `src/wifi_auth/har.py`
- Modify: `src/wifi_auth/cli.py`
- Test: `tests/test_har.py`

**Steps:**

1. Parse HAR JSON.
2. Find requests containing username-like and password-like form fields.
3. Extract URL, method, content type, field names, hidden/static fields, selected headers.
4. Redact secret values.
5. Print candidate list and save selected candidate.
6. Add tests with a small fixture HAR.

### Task 11: Implement keepalive discovery/parser

**Objective:** Detect and replay keepalive requests safely.

**Files:**
- Create: `src/wifi_auth/keepalive.py`
- Test: `tests/test_keepalive_parser.py`

**Steps:**

1. Parse meta refresh.
2. Parse obvious JavaScript timers and URL references.
3. Detect iframe refresh source.
4. Infer interval from visible phrase like `Authentication Refresh in N seconds`.
5. Apply safety margin: refresh at 80-90% of observed expiry, with min/max bounds.
6. Add tests.

### Task 12: Implement login flow

**Objective:** Perform one complete login attempt.

**Files:**
- Create: `src/wifi_auth/net/captive.py`
- Modify: `src/wifi_auth/cli.py`
- Test: `tests/test_login_flow.py`

**Steps:**

1. Run detection.
2. Fetch login page.
3. Resolve adapter.
4. Retrieve credentials.
5. Submit login.
6. Run probes again to verify success.
7. Save cookies.
8. Return structured result.

### Task 13: Build fake portal integration tests

**Objective:** Verify end-to-end behavior without touching live network.

**Files:**
- Create: `tests/fake_portal.py`
- Create: `tests/test_integration_fake_portal.py`

**Steps:**

1. Implement local HTTP server fixture.
2. Simulate unauthenticated redirects.
3. Simulate login with CSRF token.
4. Simulate keepalive page.
5. Verify full login + keepalive + recheck flow.

### Task 14: Implement daemon loop

**Objective:** Run continuously with safe retry/backoff.

**Files:**
- Create: `src/wifi_auth/daemon.py`
- Modify: `src/wifi_auth/cli.py`
- Test: `tests/test_daemon.py`

**Steps:**

1. Implement state machine.
2. Add exponential backoff.
3. Add SIGTERM/SIGINT handling.
4. Write sanitized status file.
5. Unit-test transitions with mocked detector/login/keepalive.

### Task 15: Implement systemd service installer

**Objective:** Make the service easy to install as a user daemon.

**Files:**
- Create: `src/wifi_auth/systemd.py`
- Create: `packaging/systemd/wifi-auth.service.template`
- Modify: `src/wifi_auth/cli.py`
- Test: `tests/test_systemd.py`

**Steps:**

1. Render service template with current Python executable.
2. Write to `~/.config/systemd/user/wifi-auth.service`.
3. Provide commands to enable/start/status/logs.
4. Tests verify template rendering only, not actual systemd side effects.

### Task 16: Write README and operational docs

**Objective:** Make setup safe and understandable.

**Files:**
- Create/Modify: `README.md`

**Include:**

- Scope and acceptable-use warning.
- Installation with `uv`.
- First-time setup.
- HAR capture instructions.
- Manual login/debug commands.
- systemd service installation.
- Troubleshooting keyring on Linux.
- Troubleshooting capture failures.
- How to disable/remove service.

---

## 12. Recommended First Implementation Milestone

Do not build everything at once. First milestone should be:

1. Config + credentials.
2. Probe detection.
3. Generic form parser.
4. Fake portal integration test.
5. Manual `wifi-auth login --profile fake` success.

Only after fake portal success, capture the actual IIITK request and implement the IIITK profile.

---

## 13. Open Questions to Resolve from Real Portal Data

These require either screenshots with URLs visible, HTML source, or a HAR export:

1. What is the portal host/IP?
2. Is login plain HTTP or HTTPS?
3. What are the username/password field names?
4. Are there CSRF/session hidden fields?
5. Does the portal require specific headers like `Referer` or `Origin`?
6. Does login response set cookies, or is auth entirely gateway-side by IP/MAC?
7. What request does the keepalive page make?
8. Does keepalive require cookies?
9. Does session expiry show a specific status endpoint?
10. Are there device/session limits that automation must respect?

---

## 14. Acceptance Criteria

The project is complete when:

- `uv run pytest` passes.
- Fake portal integration test proves login + keepalive.
- `wifi-auth detect --debug` correctly identifies captive/open/offline states.
- `wifi-auth capture-har` can derive a login profile from a HAR file.
- `wifi-auth login --profile iiitk` works once manually on campus network.
- `wifi-auth daemon --foreground` keeps the session alive for at least one expiry cycle without excessive requests.
- Password is stored only in OS keyring.
- Logs contain no password or cookie/token values.
- User can install/start/stop/remove the systemd user service.

---

## 15. Practical Notes for IIITK Deployment

- Prefer starting with HAR capture rather than guessing request fields from screenshots.
- If the keepalive page displays a long countdown like `Authentication Refresh in 10789 seconds`, keepalive interval should be hours, not seconds.
- Connectivity checks can be frequent; login attempts should not be.
- If credentials fail once with a clear invalid-login response, stop retrying until user manually re-runs `creds set` or `login`.
- If the portal uses a CAPTCHA or explicit consent checkbox that policy requires manually each time, do not bypass it. The service should notify the user instead.
- If the network admins provide an official client or API, prefer that over reverse-engineering the portal.

---

## 16. Optional Future Features

- Tray icon.
- Desktop notifications.
- Multi-OS service support:
  - Windows Task Scheduler/service;
  - macOS LaunchAgent.
- Browser extension companion for portals requiring JS.
- Plugin template generator:

```bash
wifi-auth plugin new my-campus
```

- Export sanitized diagnostics bundle for debugging.
- RFC 8910 captive portal API support if the network advertises it via DHCP/RA.
- Small local web UI at `localhost` for status and setup.
