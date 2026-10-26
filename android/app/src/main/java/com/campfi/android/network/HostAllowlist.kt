package com.campfi.android.network

import com.campfi.android.data.normalizeHost
import java.net.URI

class HostNotAllowedException(host: String) : SecurityException("Portal host is not approved: $host")

class ApprovedHostPolicy(approvedHosts: Set<String>) {
    private val hosts = approvedHosts.map(::normalizeHost).filter(String::isNotBlank).toSet()

    fun isAllowed(url: String): Boolean = runCatching {
        val uri = URI(url)
        val host = normalizeHost(uri.host.orEmpty())
        host.isNotBlank() && hosts.any { host == it || host.endsWith(".$it") }
    }.getOrDefault(false)

    fun requireAllowed(url: String) {
        val host = runCatching { URI(url).host.orEmpty() }.getOrDefault("unknown")
        if (!isAllowed(url)) throw HostNotAllowedException(host)
    }

    fun approvedHosts(): Set<String> = hosts
}
