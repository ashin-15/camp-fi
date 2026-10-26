package com.campfi.android.network

import java.net.HttpURLConnection
import java.net.URL

enum class ConnectivityStatus { INTERNET, CAPTIVE, OFFLINE, UNKNOWN }

data class ProbeResponse(val statusCode: Int, val location: String? = null)

fun interface ProbeTransport {
    fun execute(url: URL): ProbeResponse
}

data class ProbeResult(
    val status: ConnectivityStatus,
    val redirectUrl: String? = null,
    val statusCode: Int? = null,
)

class NetworkProbe(
    private val transport: ProbeTransport,
    private val probeUrl: URL = URL("http://connectivitycheck.gstatic.com/generate_204"),
) {
    fun check(): ProbeResult = runCatching {
        val response = transport.execute(probeUrl)
        when {
            response.statusCode == 204 -> ProbeResult(ConnectivityStatus.INTERNET, statusCode = 204)
            response.statusCode in 300..399 -> ProbeResult(
                ConnectivityStatus.CAPTIVE,
                response.location,
                response.statusCode,
            )
            response.statusCode in 200..299 -> ProbeResult(ConnectivityStatus.CAPTIVE, statusCode = response.statusCode)
            else -> ProbeResult(ConnectivityStatus.UNKNOWN, statusCode = response.statusCode)
        }
    }.getOrElse { ProbeResult(ConnectivityStatus.OFFLINE) }
}

class AndroidProbeTransport(private val opener: NetworkConnectionOpener) : ProbeTransport {
    override fun execute(url: URL): ProbeResponse {
        val connection = opener.open(url)
        return try {
            connection.instanceFollowRedirects = false
            connection.connectTimeout = 5_000
            connection.readTimeout = 5_000
            ProbeResponse(connection.responseCode, connection.getHeaderField("Location"))
        } finally {
            connection.disconnect()
        }
    }
}
