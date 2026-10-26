package com.campfi.android.wifi

import android.content.Context
import android.net.ConnectivityManager
import android.net.Network
import android.net.NetworkCapabilities
import android.net.wifi.WifiInfo
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.suspendCancellableCoroutine
import kotlinx.coroutines.withContext
import kotlinx.coroutines.withTimeoutOrNull
import kotlin.coroutines.resume

class WifiIdentityResolver(context: Context) {
    private val connectivityManager = context.applicationContext.getSystemService(ConnectivityManager::class.java)

    suspend fun awaitTargetNetwork(expectedSsid: String, timeoutMs: Long = 15_000L): Network? =
        withContext(Dispatchers.IO) {
            withTimeoutOrNull(timeoutMs) {
                currentWifiNetwork(expectedSsid)?.let { return@withTimeoutOrNull it }
                suspendCancellableCoroutine<Network?> { continuation ->
                    val request = android.net.NetworkRequest.Builder()
                        .addTransportType(NetworkCapabilities.TRANSPORT_WIFI)
                        .addCapability(NetworkCapabilities.NET_CAPABILITY_INTERNET)
                        .build()
                    lateinit var callback: ConnectivityManager.NetworkCallback
                    callback = object : ConnectivityManager.NetworkCallback() {
                        override fun onAvailable(network: Network) {
                            if (isTarget(network, expectedSsid) && continuation.isActive) {
                                continuation.resume(network)
                                runCatching { connectivityManager.unregisterNetworkCallback(this) }
                            }
                        }
                    }
                    try {
                        connectivityManager.registerNetworkCallback(request, callback)
                        continuation.invokeOnCancellation {
                            runCatching { connectivityManager.unregisterNetworkCallback(callback) }
                        }
                    } catch (_: SecurityException) {
                        if (continuation.isActive) continuation.resume(null)
                    }
                }
            }
        }

    fun currentSsid(network: Network? = connectivityManager.activeNetwork): String? {
        if (network == null) return null
        return runCatching {
            val info = connectivityManager.getNetworkCapabilities(network)?.transportInfo as? WifiInfo
            info?.ssid?.trim('"')?.takeUnless { it.isBlank() || it == "<unknown ssid>" }
        }.getOrNull()
    }

    private fun currentWifiNetwork(expectedSsid: String): Network? {
        val active = connectivityManager.activeNetwork ?: return null
        return active.takeIf { isTarget(it, expectedSsid) }
    }

    private fun isTarget(network: Network, expectedSsid: String): Boolean {
        val capabilities = connectivityManager.getNetworkCapabilities(network) ?: return false
        if (!capabilities.hasTransport(NetworkCapabilities.TRANSPORT_WIFI)) return false
        val actual = (capabilities.transportInfo as? WifiInfo)?.ssid?.trim('"')
        return actual == null || actual == "<unknown ssid>" || actual == expectedSsid
    }
}

class ConnectionEventGate(
    private val now: () -> Long = { System.currentTimeMillis() },
    private val suppressionWindowMs: Long = 30_000L,
) {
    private val lastAccepted = mutableMapOf<String, Long>()

    @Synchronized
    fun accept(key: String): Boolean {
        val current = now()
        val previous = lastAccepted[key]
        if (previous != null && current - previous < suppressionWindowMs) return false
        lastAccepted[key] = current
        return true
    }
}
