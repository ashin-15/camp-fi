package com.campfi.android.service

import android.content.Context
import com.campfi.android.data.AndroidCredentialVault
import com.campfi.android.data.LoginHistoryRepository
import com.campfi.android.data.LoginResult
import com.campfi.android.data.LoginStatus
import com.campfi.android.data.ProfileRepository
import com.campfi.android.data.StatusRepository
import com.campfi.android.data.WifiProfile
import com.campfi.android.network.AndroidProbeTransport
import com.campfi.android.network.ConnectivityStatus
import com.campfi.android.network.NetworkConnectionOpener
import com.campfi.android.network.NetworkProbe
import com.campfi.android.portal.LoginAttemptCoordinator
import com.campfi.android.portal.PortalLoginEngine
import com.campfi.android.wifi.WifiIdentityResolver

class LoginOperation(private val context: Context) {
    suspend fun run(ssid: String, portalUrl: String?): LoginResult {
        val profiles = ProfileRepository(context)
        val profile = profiles.findEnabledBySsid(ssid)
            ?: return LoginResult(LoginStatus.INVALID_CONFIGURATION, message = "No enabled profile matches the connection event.")
        return run(profile, portalUrl)
    }

    suspend fun run(profile: WifiProfile, portalUrl: String?): LoginResult {
        val resolver = WifiIdentityResolver(context)
        val network = resolver.awaitTargetNetwork(profile.ssid)
            ?: return LoginResult(LoginStatus.NETWORK_ERROR, message = "The configured Wi-Fi network is no longer available.")
        val actualPortalUrl = portalUrl ?: NetworkProbe(
            AndroidProbeTransport(NetworkConnectionOpener(network)),
        ).check().redirectUrl
        if (actualPortalUrl.isNullOrBlank()) {
            return LoginResult(LoginStatus.VERIFICATION_FAILED, message = "No captive portal redirect was found on the Wi-Fi network.")
        }
        val engine = PortalLoginEngine(AndroidCredentialVault(context))
        val coordinator = LoginAttemptCoordinator(
            engine = engine,
            history = LoginHistoryRepository(context),
            status = StatusRepository(context),
            shutdown = {},
        )
        return coordinator.run(profile, network, actualPortalUrl)
    }
}
