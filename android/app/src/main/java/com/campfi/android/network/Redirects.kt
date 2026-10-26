package com.campfi.android.network

import java.net.URL

object HtmlRedirectParser {
    private val metaPattern = Regex(
        "<meta\\b[^>]*http-equiv\\s*=\\s*[\\\"']?refresh[\\\"']?[^>]*content\\s*=\\s*[\\\"'][^\\\"']*url\\s*=\\s*([^\\\"']+)[\\\"']",
        RegexOption.IGNORE_CASE,
    )
    private val metaReversePattern = Regex(
        "<meta\\b[^>]*content\\s*=\\s*[\\\"'][^\\\"']*url\\s*=\\s*([^\\\"']+)[\\\"'][^>]*http-equiv\\s*=\\s*[\\\"']?refresh[\\\"']?",
        RegexOption.IGNORE_CASE,
    )
    private val javascriptPattern = Regex(
        "window\\.location(?:\\.href)?\\s*=\\s*[\\\"']([^\\\"']+)[\\\"']",
        RegexOption.IGNORE_CASE,
    )

    fun next(html: String, baseUrl: String): String? {
        val target = metaPattern.find(html)?.groupValues?.getOrNull(1)
            ?: metaReversePattern.find(html)?.groupValues?.getOrNull(1)
            ?: javascriptPattern.find(html)?.groupValues?.getOrNull(1)
            ?: return null
        return URL(URL(baseUrl), target.trim().trim('"', '\'', ' ')).toString()
    }
}

class RedirectNavigator(private val maxRedirects: Int = 3) {
    fun canFollow(count: Int): Boolean = count < maxRedirects
}
