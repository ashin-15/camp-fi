# camp-fi Android

This is a separate native Kotlin app; the Linux/Python implementation remains under `src/camp_fi/`.

## User flow

- Configure an SSID such as `IIITKottayam_5G`, portal username, and portal password. The app uses automatic adapter selection and its built-in approved IIITK portal host policy.
- Enable the profile. The app registers a `WifiNetworkSuggestion` with `setIsAppInteractionRequired(true)`.
- Android sends `ACTION_WIFI_NETWORK_SUGGESTION_POST_CONNECTION` after it connects. The receiver matches the SSID and dispatches one short login operation.
- Requests use `Network.openConnection()` through the connected Wi-Fi `Network`, with host allowlisting and a maximum of three redirects.
- A network-bound probe verifies internet access. The service/worker then exits; the suggestion remains installed for future reconnect events.

Credentials and cookies are encrypted with AES/GCM using a key held by Android Keystore. DataStore contains profile metadata and redacted status/history only. The app does not use accessibility automation, a VPN, root, continuous scanning, polling, periodic login, or a default keepalive timer.

## Build and test

From this directory, with Android SDK and Java 17 available:

```bash
./gradlew test
./gradlew assembleDebug
./gradlew connectedAndroidTest
./gradlew installDebug
```

The initial implementation targets API 29 and compiles against API 35. Android 13+ requires runtime Nearby Wi-Fi permission; the post-connection broadcast also requires location permission. The app requests those only when saving/enabling a profile.

Android 12+ may reject a foreground-service start while the app is backgrounded. In that case the receiver schedules a single expedited WorkManager job; it is not periodic work. OEM battery restrictions and the actual portal behavior still require physical-device validation.

HTTP is disabled globally. Cleartext is enabled only for the known Android connectivity probe and the known IIITK host in `network_security_config.xml`; other approved hosts should use HTTPS. Manual WebView fallback never injects credentials and restricts page navigation to the profile allowlist.
