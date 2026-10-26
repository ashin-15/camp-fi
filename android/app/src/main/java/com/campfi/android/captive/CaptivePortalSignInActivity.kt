package com.campfi.android.captive

import android.content.Intent
import android.net.CaptivePortal
import android.net.ConnectivityManager
import android.net.Network
import android.os.Build
import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.Button
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import androidx.lifecycle.lifecycleScope
import com.campfi.android.CampFiTheme
import com.campfi.android.data.AndroidCredentialVault
import com.campfi.android.data.LoginHistoryRepository
import com.campfi.android.data.LoginResult
import com.campfi.android.data.LoginStatus
import com.campfi.android.data.ProfileRepository
import com.campfi.android.data.StatusRepository
import com.campfi.android.data.WifiProfile
import com.campfi.android.network.ApprovedHostPolicy
import com.campfi.android.portal.LoginAttemptCoordinator
import com.campfi.android.portal.PortalLoginEngine
import com.campfi.android.portal.ManualFallbackPolicy
import com.campfi.android.wifi.WifiIdentityResolver
import kotlinx.coroutines.launch

class CaptivePortalSignInActivity : ComponentActivity() {
    private var message by mutableStateOf("Preparing captive portal login…")
    private var result by mutableStateOf<LoginResult?>(null)
    private var portalUrl: String? = null
    private var profile: WifiProfile? = null

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        if (intent.action != ConnectivityManager.ACTION_CAPTIVE_PORTAL_SIGN_IN) {
            finish()
            return
        }
        val network = parcelableExtra<Network>(ConnectivityManager.EXTRA_NETWORK) ?: run {
            finish()
            return
        }
        val captivePortal = parcelableExtra<CaptivePortal>(ConnectivityManager.EXTRA_CAPTIVE_PORTAL)
        portalUrl = intent.getStringExtra(ConnectivityManager.EXTRA_CAPTIVE_PORTAL_URL)
        setContent {
            CampFiTheme {
                Surface(modifier = Modifier.fillMaxSize()) {
                    Column(
                        modifier = Modifier.fillMaxSize().padding(20.dp),
                        verticalArrangement = Arrangement.spacedBy(12.dp),
                    ) {
                        Text("Captive portal login", style = MaterialTheme.typography.headlineSmall)
                        Text(message)
                        if (ManualFallbackPolicy.shouldOffer(result ?: LoginResult(LoginStatus.PARSE_ERROR))) {
                            Button(
                                onClick = {
                                    startActivity(Intent(this@CaptivePortalSignInActivity, ManualLoginActivity::class.java).apply {
                                        putExtra(ManualLoginActivity.EXTRA_URL, portalUrl)
                                    })
                                },
                                modifier = Modifier.fillMaxWidth(),
                            ) { Text("Open manual WebView") }
                        }
                        OutlinedButton(
                            onClick = {
                                captivePortal?.ignoreNetwork()
                                finish()
                            },
                            modifier = Modifier.fillMaxWidth(),
                        ) { Text("Ignore this network") }
                    }
                }
            }
        }
        lifecycleScope.launch {
            runLogin(network, captivePortal)
        }
    }

    private suspend fun runLogin(network: Network, captivePortal: CaptivePortal?) {
        val url = portalUrl
        if (url.isNullOrBlank()) {
            message = "Android did not provide a captive portal URL."
            result = LoginResult(LoginStatus.UNSUPPORTED_PORTAL, message = message)
            return
        }
        val resolver = WifiIdentityResolver(this)
        val ssid = resolver.currentSsid(network)
        val found = ProfileRepository(this).findEnabledBySsid(ssid.orEmpty())
        if (found == null) {
            message = "No enabled profile matches the connected Wi-Fi."
            result = LoginResult(LoginStatus.INVALID_CONFIGURATION, message = message)
            return
        }
        if (!ApprovedHostPolicy(found.approvedHosts).isAllowed(url)) {
            message = "The system portal URL is outside this profile's approved host list."
            result = LoginResult(LoginStatus.HOST_NOT_ALLOWED, message = message)
            return
        }
        profile = found
        val coordinator = LoginAttemptCoordinator(
            engine = PortalLoginEngine(AndroidCredentialVault(this)),
            history = LoginHistoryRepository(this),
            status = StatusRepository(this),
            shutdown = {},
        )
        val loginResult = coordinator.run(found, network, url)
        result = loginResult
        message = loginResult.message
        if (loginResult.succeeded) {
            captivePortal?.reportCaptivePortalDismissed()
            finish()
        }
    }

    private inline fun <reified T> parcelableExtra(key: String): T? = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
        intent.getParcelableExtra(key, T::class.java)
    } else {
        @Suppress("DEPRECATION")
        intent.getParcelableExtra(key)
    }
}
