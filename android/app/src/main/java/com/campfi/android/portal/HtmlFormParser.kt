package com.campfi.android.portal

import java.net.URL
import java.net.URLEncoder
import java.nio.charset.StandardCharsets

data class FormInfo(
    val action: String,
    val method: String,
    val fields: Map<String, String>,
    val usernameField: String?,
    val passwordField: String,
)

object HtmlFormParser {
    private val formPattern = Regex(
        "<form\\b([^>]*)>(.*?)</form\\s*>",
        setOf(RegexOption.IGNORE_CASE, RegexOption.DOT_MATCHES_ALL),
    )
    private val inputPattern = Regex("<input\\b([^>]*)/?>", RegexOption.IGNORE_CASE)
    private val buttonPattern = Regex("<button\\b([^>]*)>(.*?)</button\\s*>", setOf(RegexOption.IGNORE_CASE, RegexOption.DOT_MATCHES_ALL))
    private val attributePattern = Regex(
        """([A-Za-z_:][A-Za-z0-9_.:-]*)\s*=\s*(?:"([^"]*)"|'([^']*)'|([^\s>]+))""",
    )

    fun parse(html: String, baseUrl: String): FormInfo? {
        for (match in formPattern.findAll(html)) {
            val formAttributes = attributes(match.groupValues[1])
            val fields = linkedMapOf<String, String>()
            var usernameField: String? = null
            var passwordField: String? = null

            for (input in inputPattern.findAll(match.groupValues[2])) {
                val attrs = attributes(input.groupValues[1])
                val name = attrs["name"]?.takeIf(String::isNotBlank) ?: continue
                val type = attrs["type"].orEmpty().ifBlank { "text" }.lowercase()
                val isChecked = attrs.containsKey("checked")
                when (type) {
                    "hidden", "text", "email", "tel", "number" -> fields[name] = decode(attrs["value"].orEmpty())
                    "password" -> {
                        fields[name] = decode(attrs["value"].orEmpty())
                        passwordField = passwordField ?: name
                    }
                    "checkbox", "radio" -> if (isChecked) fields[name] = decode(attrs["value"] ?: "on")
                    "submit", "button" -> fields[name] = decode(attrs["value"].orEmpty())
                }
                if (usernameField == null && type != "password" && type != "hidden" &&
                    (name.contains("user", true) || name.contains("login", true) ||
                        name.contains("email", true) || type == "email" || type == "text")
                ) {
                    usernameField = name
                }
            }

            for (button in buttonPattern.findAll(match.groupValues[2])) {
                val attrs = attributes(button.groupValues[1])
                val name = attrs["name"]?.takeIf(String::isNotBlank)
                if (name != null) fields[name] = decode(attrs["value"].orEmpty())
            }

            if (passwordField != null) {
                val action = URL(URL(baseUrl), formAttributes["action"].orEmpty()).toString()
                val method = formAttributes["method"].orEmpty().ifBlank { "GET" }.uppercase()
                return FormInfo(action, method, fields, usernameField, passwordField)
            }
        }
        return null
    }

    fun encode(fields: Map<String, String>): String = fields.entries.joinToString("&") {
        "${urlEncode(it.key)}=${urlEncode(it.value)}"
    }

    private fun attributes(source: String): Map<String, String> {
        val result = linkedMapOf<String, String>()
        for (match in attributePattern.findAll(source)) {
            val value = match.groupValues[2].ifEmpty {
                match.groupValues[3].ifEmpty { match.groupValues[4] }
            }
            result[match.groupValues[1].lowercase()] = value
        }
        // Boolean HTML attributes such as checked have no equals sign.
        Regex("\\b(checked|selected|disabled)\\b", RegexOption.IGNORE_CASE)
            .findAll(source)
            .forEach { result.putIfAbsent(it.value.lowercase(), "") }
        return result
    }

    private fun decode(value: String): String = value
        .replace("&amp;", "&", ignoreCase = true)
        .replace("&quot;", "\"", ignoreCase = true)
        .replace("&#39;", "'", ignoreCase = true)
        .replace("&lt;", "<", ignoreCase = true)
        .replace("&gt;", ">", ignoreCase = true)
        .replace(Regex("&#x([0-9a-fA-F]+);")) { it.groupValues[1].toInt(16).toChar().toString() }
        .replace(Regex("&#([0-9]+);")) { it.groupValues[1].toInt().toChar().toString() }

    private fun urlEncode(value: String): String = URLEncoder.encode(value, StandardCharsets.UTF_8.name())
}
