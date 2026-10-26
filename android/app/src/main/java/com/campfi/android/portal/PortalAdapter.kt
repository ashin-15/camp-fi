package com.campfi.android.portal

import com.campfi.android.data.PortalAdapterType
import com.campfi.android.data.ProfileCredentials
import com.campfi.android.network.NetworkHttpClient
import com.campfi.android.network.NetworkResponse

sealed interface PreparedLogin

data class FormPreparedLogin(val form: FormInfo) : PreparedLogin

data class FortinetPreparedLogin(
    val magic: String,
    val loginUrl: String,
    val logoutUrl: String,
) : PreparedLogin

interface PortalAdapter {
    val type: PortalAdapterType
    val name: String
    fun matches(html: String, url: String): Boolean
    fun prepareLogin(html: String, url: String): PreparedLogin
    fun submitLogin(client: NetworkHttpClient, prepared: PreparedLogin, credentials: ProfileCredentials): NetworkResponse
}

class GenericFormAdapter : PortalAdapter {
    override val type = PortalAdapterType.GENERIC_FORM
    override val name = "generic_form"

    override fun matches(html: String, url: String): Boolean = HtmlFormParser.parse(html, url) != null

    override fun prepareLogin(html: String, url: String): PreparedLogin = FormPreparedLogin(
        HtmlFormParser.parse(html, url) ?: error("No login form found"),
    )

    override fun submitLogin(
        client: NetworkHttpClient,
        prepared: PreparedLogin,
        credentials: ProfileCredentials,
    ): NetworkResponse {
        val form = (prepared as? FormPreparedLogin)?.form ?: error("Generic adapter received the wrong form")
        val data = form.fields.toMutableMap()
        form.usernameField?.let { data[it] = credentials.username }
        data[form.passwordField] = credentials.password
        return client.submit(form.method, form.action, data)
    }
}

class IIITKAdapter : PortalAdapter {
    override val type = PortalAdapterType.IIITK
    override val name = "iiitk"

    override fun matches(html: String, url: String): Boolean =
        url.contains("auth.iiitkottayam.ac.in", ignoreCase = true) ||
            html.contains("auth.iiitkottayam.ac.in", ignoreCase = true)

    override fun prepareLogin(html: String, url: String): PreparedLogin = FormPreparedLogin(
        HtmlFormParser.parse(html, url) ?: error("No login form found in IIITK portal page"),
    )

    override fun submitLogin(
        client: NetworkHttpClient,
        prepared: PreparedLogin,
        credentials: ProfileCredentials,
    ): NetworkResponse = GenericFormAdapter().submitLogin(client, prepared, credentials)
}

class FortinetAdapter : PortalAdapter {
    override val type = PortalAdapterType.FORTINET
    override val name = "fortinet"

    override fun matches(html: String, url: String): Boolean =
        html.contains(Regex("\\bmagic\\b", RegexOption.IGNORE_CASE)) &&
            (url.contains("auth.iiitkottayam.ac.in", true) || url.contains(":1000") ||
                html.contains("fortinet", true) || html.contains("fgtauth", true))

    override fun prepareLogin(html: String, url: String): PreparedLogin {
        val form = HtmlFormParser.parse(html, url)
        val magic = form?.fields?.entries?.firstOrNull { it.key.equals("magic", true) }?.value
            ?.takeIf(String::isNotBlank)
            ?: Regex("name\\s*=\\s*[\"']magic[\"']?[^>]*value\\s*=\\s*[\"']([^\"']+)", RegexOption.IGNORE_CASE)
                .find(html)?.groupValues?.getOrNull(1)
            ?: error("No magic token found in Fortinet portal page")
        val base = url.substringBefore('?')
        val loginUrl = form?.action ?: base
        val logoutUrl = if (base.contains("/login", true)) {
            base.replaceFirst(Regex("/login", RegexOption.IGNORE_CASE), "/logout")
        } else {
            "$base/logout"
        }
        return FortinetPreparedLogin(magic, loginUrl, logoutUrl)
    }

    override fun submitLogin(
        client: NetworkHttpClient,
        prepared: PreparedLogin,
        credentials: ProfileCredentials,
    ): NetworkResponse {
        val login = prepared as? FortinetPreparedLogin ?: error("Fortinet adapter received the wrong login")
        runCatching { client.get("${login.logoutUrl}?${login.magic}", followRedirects = false) }
        return client.submit(
            "POST",
            login.loginUrl,
            mapOf("magic" to login.magic, "username" to credentials.username, "password" to credentials.password),
        )
    }
}

object PortalAdapterFactory {
    private val adapters = listOf(FortinetAdapter(), IIITKAdapter(), GenericFormAdapter())

    fun select(type: PortalAdapterType, html: String, url: String): PortalAdapter? {
        return if (type == PortalAdapterType.AUTO) {
            adapters.firstOrNull { it.matches(html, url) }
        } else {
            adapters.firstOrNull { it.type == type && it.matches(html, url) }
        }
    }
}

object ManualFallbackPolicy {
    fun shouldOffer(result: com.campfi.android.data.LoginResult): Boolean =
        result.status == com.campfi.android.data.LoginStatus.UNSUPPORTED_PORTAL ||
            result.status == com.campfi.android.data.LoginStatus.PARSE_ERROR
}
