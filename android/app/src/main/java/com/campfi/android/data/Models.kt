package com.campfi.android.data

import java.util.UUID

enum class PortalAdapterType {
    AUTO,
    IIITK,
    FORTINET,
    GENERIC_FORM,
}

/** Built-in policy for the IIITK-focused app; users do not need to configure portal internals. */
object DefaultPortalConfig {
    val adapterType: PortalAdapterType = PortalAdapterType.AUTO
    val approvedHosts: Set<String> = setOf(
        "auth.iiitkottayam.ac.in",
        "connectivitycheck.gstatic.com",
        "172.16.222.1",
    )
}

data class WifiProfile(
    val id: String = UUID.randomUUID().toString(),
    val ssid: String,
    val adapterType: PortalAdapterType,
    val approvedHosts: Set<String>,
    val enabled: Boolean = true,
)

data class ProfileCredentials(
    val username: String,
    val password: String,
    val wifiPsk: String? = null,
    val cookies: Map<String, String> = emptyMap(),
)

enum class LoginStatus {
    SUCCESS,
    AUTH_FAILED,
    NETWORK_ERROR,
    UNSUPPORTED_PORTAL,
    HOST_NOT_ALLOWED,
    REDIRECT_LIMIT_EXCEEDED,
    PARSE_ERROR,
    VERIFICATION_FAILED,
    INVALID_CONFIGURATION,
    CANCELLED,
    ALREADY_IN_PROGRESS,
    PROTOCOL_ERROR,
}

data class LoginResult(
    val status: LoginStatus,
    val adapterName: String? = null,
    val message: String = "",
    val attempts: Int = 1,
    val verified: Boolean = false,
) {
    val succeeded: Boolean get() = status == LoginStatus.SUCCESS && verified
}

data class LoginHistoryEntry(
    val timestamp: Long,
    val profileId: String,
    val ssid: String,
    val status: LoginStatus,
    val adapterName: String?,
    val message: String,
)

data class StatusSnapshot(
    val timestamp: Long = 0L,
    val profileId: String? = null,
    val ssid: String? = null,
    val status: LoginStatus? = null,
    val message: String = "Waiting for a configured Wi-Fi connection.",
)

fun normalizeHost(value: String): String = value
    .trim()
    .lowercase()
    .removePrefix("http://")
    .removePrefix("https://")
    .substringBefore('/')
    .substringBefore(':')
    .trimEnd('.')
