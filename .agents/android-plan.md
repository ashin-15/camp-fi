# Android captive-portal auto-login plan

## Status

Approved planning document. No Android implementation has been started yet.

## Goal

Build a native Kotlin Android app that lets the user configure a Wi-Fi profile and captive-portal credentials once, then performs one automatic portal login whenever Android connects to the configured SSID.

The desired lifecycle is:

```text
User configures profile
        ↓
Android connects to the configured SSID
        ↓
App receives a connection event
        ↓
App logs into the captive portal once
        ↓
App verifies internet access
        ↓
App stops its temporary login worker/service
        ↓
Android continues normal Wi-Fi operation
```

The app must not continuously scan or poll after a successful login.

## Repository context

The current project is the Python/Linux `camp-fi` daemon. Important existing components are:

- `src/camp_fi/daemon.py`: polling daemon and login state machine.
- `src/camp_fi/net/probes.py`: captive/internet/offline probing.
- `src/camp_fi/net/captive.py`: portal discovery, redirects, adapter selection, login verification.
- `src/camp_fi/portals/generic_form.py`: generic HTML form adapter.
- `src/camp_fi/portals/iiitk.py`: IIITK adapter.
- `src/camp_fi/portals/fortinet.py`: Fortinet adapter and magic-token flow.
- `src/camp_fi/credentials.py`: Linux OS keyring storage.
- `src/camp_fi/session_store.py`: private cookie persistence.
- `tests/test_fake_portal.py`: fake portal and keepalive fixtures.
- `tests/test_adapters.py`: adapter matching tests.

The Android version should be a separate native Kotlin project, likely under `android/`, while the Linux implementation remains intact.

## Main architectural decision

Use a native Kotlin Android application rather than embedding Python, using Flutter without native networking code, a VPN, or an Accessibility Service.

Reasoning:

- Android Wi-Fi and captive-portal APIs are native platform APIs.
- Android background execution rules require explicit lifecycle handling.
- Network requests must be bound to the specific captive Wi-Fi `Network`.
- A native app gives direct access to `WifiNetworkSuggestion`, `NetworkCallback`, `CaptivePortal`, foreground-service rules, and Android Keystore.

## Event-driven connection model

### Primary mechanism: Wi-Fi suggestion

When the user enables a profile, add the configured SSID through `WifiNetworkSuggestion` with `setIsAppInteractionRequired(true)`.

For an open institutional network:

```kotlin
WifiNetworkSuggestion.Builder()
    .setSsid("IIITKottayam_5G")
    .setIsAppInteractionRequired(true)
    .build()
```

For WPA/WPA3 Wi-Fi, configure the Wi-Fi PSK separately from the captive-portal username/password.

Android should remain responsible for choosing and connecting to the suggested network. The app should not repeatedly invoke scans.

### Wake-up event

Handle:

```kotlin
WifiManager.ACTION_WIFI_NETWORK_SUGGESTION_POST_CONNECTION
```

The receiver should:

1. Confirm that the event belongs to a configured suggestion.
2. Resolve the connected `Network`.
3. Match the SSID/profile.
4. Start one short authentication operation.
5. Stop after success or bounded failure.

The receiver itself must remain lightweight. The network operation should run in a short-lived service or appropriate expedited worker, subject to Android background-start restrictions.

### Manual Wi-Fi fallback

If the user connects through Android Settings without the app's suggestion, the app cannot guarantee a wake-up after its process is stopped. Provide one of these fallbacks:

- User launches the app and taps `Login now`.
- Android invokes the app's captive-portal sign-in activity.
- Optional user-enabled monitoring mode keeps a foreground service active.

This limitation must be documented in the UI if manual Wi-Fi provisioning is supported.

## State machine

```text
DISABLED
   ↓ user enables profile

WAITING_FOR_TARGET_WIFI
   ↓ Android connects to suggested SSID

CONNECTION_EVENT_RECEIVED
   ↓ verify SSID/profile/network

AUTHENTICATING
   ↓ portal request

VERIFYING_LOGIN
   ↓ successful network-bound probe

AUTHENTICATED
   ↓ stop temporary worker/service/callback

WAITING_FOR_TARGET_WIFI
```

Failure path:

```text
AUTHENTICATING
   ↓ failure

RETRY_CURRENT_CONNECTION
   ↓ bounded exponential retries

LOGIN_FAILED
   ↓ notification and stop

WAITING_FOR_TARGET_WIFI
```

Only one login operation may run for a network connection at a time.

## Android application structure

Start with one Gradle application module:

```text
android/app/src/main/java/<package>/
├── data/
│   ├── ProfileRepository.kt
│   ├── CredentialVault.kt
│   └── LoginHistoryRepository.kt
├── wifi/
│   ├── WifiSuggestionManager.kt
│   ├── WifiConnectionReceiver.kt
│   └── WifiIdentityResolver.kt
├── network/
│   ├── NetworkProbe.kt
│   └── NetworkHttpClient.kt
├── portal/
│   ├── PortalLoginEngine.kt
│   ├── PortalAdapter.kt
│   ├── IIITKAdapter.kt
│   ├── FortinetAdapter.kt
│   └── GenericFormAdapter.kt
├── service/
│   └── OneShotLoginService.kt
├── captive/
│   └── CaptivePortalSignInActivity.kt
└── ui/
    ├── ProfileScreen.kt
    ├── StatusScreen.kt
    └── SettingsScreen.kt
```

Recommended libraries:

- Kotlin and Kotlin Coroutines.
- Jetpack Compose and ViewModel.
- DataStore for profile settings.
- Room for bounded login history, if history is included in v1.
- Jsoup for HTML form parsing.
- OkHttp or `HttpURLConnection` for portal HTTP requests.
- AndroidX WebKit for a controlled manual WebView fallback.
- WorkManager only for recovery/reconciliation, not frequent keepalive polling.

## One-shot login flow

`OneShotLoginCoordinator` should port the current `execute_login()` behavior:

1. Receive a connected Android `Network` and portal URL.
2. Build an HTTP client bound to that `Network`.
3. Load encrypted profile cookies.
4. Fetch the portal page.
5. Follow limited HTML/meta/JavaScript redirects.
6. Validate the final host against the profile allowlist.
7. Select an adapter.
8. Preserve hidden fields and CSRF/redirect values.
9. Submit the portal username and password.
10. Save cookies.
11. Verify internet access through the same `Network`.
12. Return a structured login result.
13. Report captive-portal dismissal when applicable.
14. Stop the temporary worker/service.

The request must use the supplied Wi-Fi `Network`; otherwise Android may send the request through mobile data.

Prefer `Network.openConnection(url)` or an HTTP client configured with the network's socket factory. Avoid global process binding unless required by the captive-portal activity.

## Portal adapters

Port these adapters first:

1. `IIITKAdapter`.
2. `FortinetAdapter`.
3. `GenericFormAdapter`.
4. Manual/WebView fallback for unsupported or JavaScript-heavy portals.

The adapter contract should preserve the existing concepts:

```text
matches(html, url)
prepareLogin(...)
submitLogin(...)
getKeepalive(...)
```

The generic adapter should support:

- Relative and absolute form actions.
- GET and POST methods.
- Hidden fields.
- Username and password field detection.
- URL encoding.
- Multiple forms.
- Submit controls and checkbox values where required.

The Android version should improve security over the current generic fallback by requiring approved portal hosts before submitting credentials.

## Captive portal fallback

Implement an activity for:

```kotlin
ConnectivityManager.ACTION_CAPTIVE_PORTAL_SIGN_IN
```

Read:

- `ConnectivityManager.EXTRA_NETWORK`.
- `ConnectivityManager.EXTRA_CAPTIVE_PORTAL`.
- `ConnectivityManager.EXTRA_CAPTIVE_PORTAL_URL`.

Use the supplied `Network` for all portal communication. On verified success, call:

```kotlin
captivePortal.reportCaptivePortalDismissed()
```

On explicit user rejection, call `ignoreNetwork()`.

Some OEMs use their own captive-portal implementation, so this is a fallback rather than the only event source.

## Background execution policy

The default mode is one-shot:

- No continuous scan.
- No periodic login timer.
- No permanent foreground service after success.
- No keepalive timer after success.

The app may use a short-lived foreground service for the login operation. Android 12+ background foreground-service start restrictions must be tested on physical devices. If the system rejects the start, use an expedited worker where possible and show a user notification when user action is required.

Offer an optional advanced monitoring mode only if the portal requires session keepalives or reauthentication while the phone remains connected. That mode requires a visible foreground-service notification.

## Keepalive decision

The approved default pipeline does not maintain keepalives after successful login. Consequently, if the portal session expires while the device remains connected, there may be no new connection event to trigger a login.

If this becomes a requirement, add a separate persistent-monitoring mode rather than silently reintroducing background polling.

## Secure storage

Use an Android Keystore-backed encryption key and store encrypted values in app-internal storage.

Requirements:

- Never store passwords in plain DataStore or SharedPreferences.
- Never log passwords, cookies, tokens, or complete credential-bearing URLs.
- Store cookies encrypted and clear them when a profile is deleted.
- Exclude sensitive data from Android backup.
- Do not store BSSID/MAC data unless required.
- Keep credentials in memory only for the login operation.
- Protect settings with optional biometric/device authentication without requiring authentication for every background login.

## Android permissions

Evaluate these permissions during implementation:

- `INTERNET`.
- `ACCESS_NETWORK_STATE`.
- `ACCESS_WIFI_STATE`.
- `CHANGE_WIFI_STATE`.
- `NEARBY_WIFI_DEVICES` on Android 13+.
- `ACCESS_FINE_LOCATION` for older Android versions and APIs that still require it.
- `POST_NOTIFICATIONS` on Android 13+.
- `FOREGROUND_SERVICE` and the appropriate API 34+ service-type permission if a foreground service is used.
- `CHANGE_NETWORK_STATE` only if required by the selected network-binding approach.

Request permissions only when the user enables the relevant feature.

## Security requirements

The Android version must not blindly copy the reference project's risky defaults:

- Do not enable cleartext traffic globally.
- Restrict cleartext exceptions to known portal hosts where unavoidable.
- Do not follow redirects to unrelated hosts.
- Do not submit credentials to arbitrary generic forms without profile approval.
- Prefer HTTPS portal endpoints.
- Do not use Accessibility Service automation.
- Do not use an unrestricted JavaScript bridge in WebView.
- Redact tokens and credentials from logs and history.

HTTP-only captive portals require an explicit risk decision because a malicious access point can imitate them.

## Reference project findings: `wifix2`

Reference: <https://github.com/Noelithub77/wifix2>

Useful parts to study:

- `ConnectivityManager.NetworkCallback` for Wi-Fi network events.
- `LinkProperties` for default-route gateway discovery.
- `Network.openConnection()` for network-bound portal requests.
- `CaptivePortalActivity` and `reportCaptivePortalDismissed()`.
- Compose UI structure.

Do not copy these behaviors unchanged:

- Its 30-minute periodic login scheduler conflicts with the approved one-shot flow.
- Its password storage uses plain `SharedPreferences`.
- Its manifest enables global cleartext traffic.
- Its login logic relies on hardcoded gateway/form details that belong in a profile-specific adapter.
- Its `NET_CAPABILITY_INTERNET` handling should be supplemented with `VALIDATED`, `CAPTIVE_PORTAL`, and a network-bound probe.

## Implementation phases

### Phase 1: Feasibility spike

- Test the actual IIITK network with a physical Android device.
- Confirm the reported network capabilities.
- Confirm the captive portal URL and gateway behavior.
- Test direct HTTP login through `Network.openConnection()`.
- Determine whether IIITK requires JavaScript or only form submission.
- Test the Wi-Fi suggestion post-connection event after the app process is closed.
- Test Android 12+ background execution behavior.

### Phase 2: Android foundation

- Create the native Kotlin/Gradle project under `android/`.
- Configure Compose and target SDK.
- Use Android 10/API 29+ as the first supported baseline unless device requirements require older support.
- Implement profile storage and encrypted credential storage.
- Implement basic status UI.

### Phase 3: Wi-Fi provisioning and event receiver

- Implement `WifiNetworkSuggestion` registration/removal.
- Implement user approval and permission handling.
- Implement `ACTION_WIFI_NETWORK_SUGGESTION_POST_CONNECTION` receiver.
- Match events to configured profiles.
- Ensure no continuous scanning or polling is used.

### Phase 4: One-shot portal engine

- Port login models and adapters.
- Implement network-bound HTTP.
- Port cookies and redirect handling.
- Implement IIITK login first.
- Add login verification and bounded retry/backoff.
- Stop the worker/service after completion.

### Phase 5: Fallbacks and hardening

- Add Fortinet and generic adapters.
- Add captive-portal sign-in activity.
- Add manual WebView fallback.
- Add host allowlists and cleartext restrictions.
- Add redacted history and notifications.

### Phase 6: Device testing and release

- Test Android 10 through the latest supported version.
- Test Pixel and Samsung devices at minimum.
- Test mobile data enabled/disabled, VPN, Private DNS, reboot, lock screen, battery optimization, and manual Wi-Fi disconnection.
- Build signed APK/AAB and review foreground-service/permission requirements before distribution.

## Testing plan

Reuse the existing fixtures from `tests/test_fake_portal.py` and `tests/test_adapters.py` as Android test resources.

Unit tests should cover:

- Form parsing.
- Hidden fields and CSRF values.
- Relative URLs.
- GET/POST submission.
- IIITK and Fortinet matching.
- Redirect limits.
- Host allowlists.
- Cookie persistence.
- Login result classification.
- Backoff and duplicate-attempt prevention.

Integration tests should cover:

- Captive redirect.
- Successful login.
- Invalid credentials.
- Expired cookies.
- Unsupported portal.
- Network loss during login.
- Repeated connection events.
- Login success followed by service/worker shutdown.

## Acceptance criteria

1. User can configure `IIITKottayam_5G` and portal credentials.
2. App registers the configured network suggestion.
3. Android connects to the target network.
4. App receives the post-connection event.
5. App submits credentials once through the target Wi-Fi network.
6. App verifies internet access through that same network.
7. App stops its temporary login process after success.
8. No continuous scan or polling runs after success.
9. A later reconnect triggers a new one-shot login.
10. Credentials and cookies are encrypted at rest.
11. Failed login attempts stop after bounded retries.
12. Unsupported portals have a manual fallback.

## Checks and current state

- Repository: `/home/ashin/Projects/wifi-auther`.
- Current branch: `main`.
- Worktree was clean before saving this plan.
- No Android project has been created.
- No implementation, build, or Android device test has been run.

## Next concrete step

Run the Phase 1 feasibility spike on a physical Android device connected to `IIITKottayam_5G`, then create the Android project only after confirming that network-bound direct login succeeds and that the Wi-Fi suggestion event can wake the app on the target Android versions.

## Official Android references

- [Wi-Fi suggestion API](https://developer.android.com/develop/connectivity/wifi/wifi-suggest)
- [Read network state](https://developer.android.com/develop/connectivity/network-ops/reading-network-state)
- [Captive portal API](https://developer.android.com/about/versions/11/features/captive-portal)
- [Wi-Fi permissions](https://developer.android.com/develop/connectivity/wifi/wifi-permissions)
- [Foreground-service launch restrictions](https://developer.android.com/develop/background-work/services/fgs/restrictions-bg-start)
- [Android Keystore](https://developer.android.com/privacy-and-security/keystore)
