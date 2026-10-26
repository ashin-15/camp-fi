package com.campfi.android.network

import android.net.Network
import java.io.BufferedInputStream
import java.net.HttpURLConnection
import java.net.URI
import java.net.URL
import java.net.URLEncoder
import java.nio.charset.StandardCharsets

data class NetworkResponse(
    val statusCode: Int,
    val url: String,
    val body: String,
    val headers: Map<String, List<String>>,
)

class RedirectLimitException : IllegalStateException("Portal redirect limit exceeded")

class CookieJar(initial: Map<String, String> = emptyMap()) {
    private val values = initial.toMutableMap()

    fun headerValue(): String = values.entries.joinToString("; ") { "${it.key}=${it.value}" }

    fun capture(headers: Map<String, List<String>>) {
        headers.entries.filter { it.key.equals("Set-Cookie", ignoreCase = true) }
            .flatMap { it.value }
            .forEach { raw ->
                val first = raw.substringBefore(';')
                val separator = first.indexOf('=')
                if (separator > 0) values[first.substring(0, separator).trim()] = first.substring(separator + 1).trim()
            }
    }

    fun snapshot(): Map<String, String> = values.toMap()
}

class NetworkHttpClient(
    private val network: Network,
    private val hostPolicy: ApprovedHostPolicy,
    val cookies: CookieJar = CookieJar(),
    private val maxRedirects: Int = 3,
    private val timeoutMs: Int = 10_000,
) {
    fun get(url: String, followRedirects: Boolean = true): NetworkResponse =
        execute("GET", url, emptyMap(), followRedirects)

    fun submit(method: String, url: String, data: Map<String, String>): NetworkResponse =
        execute(method.uppercase(), url, data, followRedirects = true)

    private fun execute(
        method: String,
        url: String,
        data: Map<String, String>,
        followRedirects: Boolean,
    ): NetworkResponse {
        var currentUrl = url
        var currentMethod = method
        var currentData = data
        var redirects = 0

        while (true) {
            hostPolicy.requireAllowed(currentUrl)
            val response = requestOnce(currentMethod, currentUrl, currentData)
            if (!followRedirects || response.statusCode !in REDIRECT_CODES) return response

            val location = response.headers.entries
                .firstOrNull { it.key.equals("Location", ignoreCase = true) }
                ?.value
                ?.firstOrNull()
                ?: return response
            if (redirects >= maxRedirects) throw RedirectLimitException()
            currentUrl = URL(URL(currentUrl), location).toString()
            redirects += 1
            if (response.statusCode == HttpURLConnection.HTTP_SEE_OTHER ||
                (response.statusCode in 301..302 && currentMethod != "GET")
            ) {
                currentMethod = "GET"
                currentData = emptyMap()
            }
        }
    }

    private fun requestOnce(method: String, url: String, data: Map<String, String>): NetworkResponse {
        val requestUrl = if (method == "GET" && data.isNotEmpty()) appendQuery(url, data) else url
        val connection = network.openConnection(URL(requestUrl)) as HttpURLConnection
        try {
            connection.requestMethod = method
            connection.connectTimeout = timeoutMs
            connection.readTimeout = timeoutMs
            connection.instanceFollowRedirects = false
            connection.useCaches = false
            cookies.headerValue().takeIf(String::isNotBlank)?.let { connection.setRequestProperty("Cookie", it) }
            if (method == "POST" || method == "PUT") {
                connection.doOutput = true
                connection.setRequestProperty("Content-Type", "application/x-www-form-urlencoded")
                val body = formEncode(data)
                connection.setRequestProperty("Content-Length", body.toByteArray().size.toString())
                connection.outputStream.use { it.write(body.toByteArray(StandardCharsets.UTF_8)) }
            }
            val status = connection.responseCode
            val headers = connection.headerFields.filterKeys { it != null }
                .mapKeys { it.key!! }
                .mapValues { it.value.orEmpty() }
            val stream = if (status >= 400) connection.errorStream else connection.inputStream
            val body = stream?.let { readLimited(it) }.orEmpty()
            cookies.capture(headers)
            return NetworkResponse(status, requestUrl, body, headers)
        } finally {
            connection.disconnect()
        }
    }

    private fun appendQuery(url: String, data: Map<String, String>): String {
        val separator = if (URI(url).query == null) "?" else "&"
        return url + separator + formEncode(data)
    }

    private fun formEncode(data: Map<String, String>): String = data.entries.joinToString("&") {
        "${encode(it.key)}=${encode(it.value)}"
    }

    private fun encode(value: String): String = URLEncoder.encode(value, StandardCharsets.UTF_8.name())

    private fun readLimited(stream: java.io.InputStream, maxBytes: Int = 1_048_576): String {
        BufferedInputStream(stream).use { input ->
            val output = java.io.ByteArrayOutputStream()
            val buffer = ByteArray(8192)
            var total = 0
            while (total < maxBytes) {
                val count = input.read(buffer, 0, minOf(buffer.size, maxBytes - total))
                if (count < 0) break
                output.write(buffer, 0, count)
                total += count
            }
            return output.toString(StandardCharsets.UTF_8.name())
        }
    }

    private companion object {
        val REDIRECT_CODES = setOf(301, 302, 303, 307, 308)
    }
}

class NetworkConnectionOpener(private val network: Network) {
    fun open(url: URL): HttpURLConnection = network.openConnection(url) as HttpURLConnection
}
