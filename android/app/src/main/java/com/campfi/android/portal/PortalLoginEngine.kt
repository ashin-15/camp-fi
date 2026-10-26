package com.campfi.android.portal

import android.net.Network
import com.campfi.android.data.LoginResult
import com.campfi.android.data.LoginStatus
import com.campfi.android.data.ProfileCredentials
import com.campfi.android.data.WifiProfile
import com.campfi.android.data.CredentialVault
import com.campfi.android.network.AndroidProbeTransport
import com.campfi.android.network.ApprovedHostPolicy
import com.campfi.android.network.HtmlRedirectParser
import com.campfi.android.network.NetworkConnectionOpener
import com.campfi.android.network.NetworkHttpClient
import com.campfi.android.network.NetworkProbe
import com.campfi.android.network.RedirectLimitException
import com.campfi.android.network.HostNotAllowedException

class PortalLoginEngine(
    private val vault: CredentialVault,
    private val probeFactory: (Network) -> NetworkProbe = { network ->
        NetworkProbe(AndroidProbeTransport(NetworkConnectionOpener(network)))
    },
) {
    suspend fun login(profile: WifiProfile, network: Network, portalUrl: String): LoginResult {
        val credentials = vault.get(profile.id)
            ?: return LoginResult(LoginStatus.INVALID_CONFIGURATION, message = "Credentials are not configured.")
        if (credentials.username.isBlank() || credentials.password.isBlank() || profile.approvedHosts.isEmpty()) {
            return LoginResult(LoginStatus.INVALID_CONFIGURATION, message = "Username, password, and approved hosts are required.")
        }

        return try {
            val policy = ApprovedHostPolicy(profile.approvedHosts)
            policy.requireAllowed(portalUrl)
            val client = NetworkHttpClient(network, policy, cookies = com.campfi.android.network.CookieJar(credentials.cookies))
            var response = client.get(portalUrl, followRedirects = true)
            var redirectCount = 0
            while (true) {
                val next = HtmlRedirectParser.next(response.body, response.url) ?: break
                if (redirectCount >= 3) throw RedirectLimitException()
                policy.requireAllowed(next)
                response = client.get(next, followRedirects = true)
                redirectCount += 1
            }

            if (response.statusCode !in 200..399) {
                return LoginResult(
                    LoginClassifier.fromHttpStatus(response.statusCode),
                    message = "Portal page returned HTTP ${response.statusCode}.",
                )
            }
            val adapter = PortalAdapterFactory.select(profile.adapterType, response.body, response.url)
                ?: return LoginResult(LoginStatus.UNSUPPORTED_PORTAL, message = "No configured adapter matched the portal.")
            val prepared = runCatching { adapter.prepareLogin(response.body, response.url) }.getOrElse {
                return LoginResult(LoginStatus.PARSE_ERROR, adapterName = adapter.name, message = "The portal form could not be parsed.")
            }
            val loginResponse = adapter.submitLogin(client, prepared, credentials)
            if (loginResponse.statusCode !in 200..399) {
                return LoginResult(
                    LoginClassifier.fromHttpStatus(loginResponse.statusCode),
                    adapterName = adapter.name,
                    message = "Portal rejected the login request.",
                )
            }

            val verification = probeFactory(network).check()
            if (verification.status != com.campfi.android.network.ConnectivityStatus.INTERNET) {
                return LoginResult(
                    LoginStatus.VERIFICATION_FAILED,
                    adapterName = adapter.name,
                    message = "Login submitted, but network-bound internet verification failed.",
                )
            }
            vault.updateCookies(profile.id, client.cookies.snapshot())
            LoginResult(
                status = LoginStatus.SUCCESS,
                adapterName = adapter.name,
                message = "Internet access verified through the configured Wi-Fi network.",
                verified = true,
            )
        } catch (_: HostNotAllowedException) {
            LoginResult(LoginStatus.HOST_NOT_ALLOWED, message = "The portal URL or redirect is outside the approved host list.")
        } catch (_: RedirectLimitException) {
            LoginResult(LoginStatus.REDIRECT_LIMIT_EXCEEDED, message = "The portal exceeded the redirect limit.")
        } catch (_: java.net.UnknownHostException) {
            LoginResult(LoginStatus.NETWORK_ERROR, message = "The portal host could not be reached.")
        } catch (_: java.io.IOException) {
            LoginResult(LoginStatus.NETWORK_ERROR, message = "The Wi-Fi network was unavailable during login.")
        } catch (_: SecurityException) {
            LoginResult(LoginStatus.HOST_NOT_ALLOWED, message = "The portal request was blocked by the host policy.")
        } catch (_: Exception) {
            LoginResult(LoginStatus.PROTOCOL_ERROR, message = "The portal login protocol failed.")
        }
    }
}

class LoginAttemptCoordinator(
    private val engine: PortalLoginEngine,
    private val history: com.campfi.android.data.LoginHistoryRepository,
    private val status: com.campfi.android.data.StatusRepository,
    private val retryPolicy: RetryPolicy = RetryPolicy(),
    private val shutdown: () -> Unit,
) {
    private val lifecycle = OneShotLifecycle(shutdown)

    suspend fun run(profile: WifiProfile, network: Network, portalUrl: String): LoginResult {
        return lifecycle.run {
            val outcome = retryPolicy.execute(
                operation = { engine.login(profile, network, portalUrl) },
                shouldRetry = { result -> result.status == LoginStatus.NETWORK_ERROR || result.status == LoginStatus.VERIFICATION_FAILED },
            )
            val result = outcome.value.copy(attempts = outcome.attempts)
            history.record(
                com.campfi.android.data.LoginHistoryEntry(
                    timestamp = System.currentTimeMillis(),
                    profileId = profile.id,
                    ssid = profile.ssid,
                    status = result.status,
                    adapterName = result.adapterName,
                    message = result.message,
                ),
            )
            status.update(profile, result)
            result
        }
    }
}
