package com.campfi.android.captive

import android.app.Activity
import android.os.Bundle
import android.webkit.WebResourceRequest
import android.webkit.WebView
import android.webkit.WebViewClient
import android.widget.Toast
import com.campfi.android.data.ProfileRepository
import com.campfi.android.network.ApprovedHostPolicy
import com.campfi.android.wifi.WifiIdentityResolver
import kotlinx.coroutines.MainScope
import kotlinx.coroutines.cancel
import kotlinx.coroutines.launch

/** User-driven fallback for portals that need JavaScript or an unsupported form flow. */
class ManualLoginActivity : Activity() {
    private val scope = MainScope()
    private var webView: WebView? = null

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        val initialUrl = intent.getStringExtra(EXTRA_URL)
        if (initialUrl.isNullOrBlank()) {
            finish()
            return
        }
        scope.launch {
            val ssid = WifiIdentityResolver(this@ManualLoginActivity).currentSsid()
            val profile = ProfileRepository(this@ManualLoginActivity).findEnabledBySsid(ssid.orEmpty())
            if (profile == null || !ApprovedHostPolicy(profile.approvedHosts).isAllowed(initialUrl)) {
                Toast.makeText(this@ManualLoginActivity, "This portal is not approved for the active profile.", Toast.LENGTH_LONG).show()
                finish()
                return@launch
            }
            val view = WebView(this@ManualLoginActivity).apply {
                settings.javaScriptEnabled = true
                settings.allowFileAccess = false
                settings.allowContentAccess = false
                settings.domStorageEnabled = true
                webViewClient = object : WebViewClient() {
                    override fun shouldOverrideUrlLoading(view: WebView, request: WebResourceRequest): Boolean {
                        return !ApprovedHostPolicy(profile.approvedHosts).isAllowed(request.url.toString())
                    }
                }
                loadUrl(initialUrl)
            }
            webView = view
            setContentView(view)
        }
    }

    override fun onDestroy() {
        webView?.apply {
            stopLoading()
            destroy()
        }
        scope.cancel()
        super.onDestroy()
    }

    companion object {
        const val EXTRA_URL = "com.campfi.android.extra.MANUAL_PORTAL_URL"
    }
}
