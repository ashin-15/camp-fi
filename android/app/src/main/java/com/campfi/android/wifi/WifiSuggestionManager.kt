package com.campfi.android.wifi

import android.content.Context
import android.net.wifi.WifiManager
import android.net.wifi.WifiNetworkSuggestion
import com.campfi.android.data.WifiProfile

enum class SuggestionResult { SUCCESS, PERMISSION_REQUIRED, INVALID_PSK, SYSTEM_REJECTED }

class WifiSuggestionManager(context: Context) {
    private val wifiManager = context.applicationContext.getSystemService(WifiManager::class.java)

    fun register(profile: WifiProfile, wifiPsk: String?): SuggestionResult {
        val suggestion = buildSuggestion(profile, wifiPsk) ?: return SuggestionResult.INVALID_PSK
        return try {
            val status = wifiManager.addNetworkSuggestions(listOf(suggestion))
            if (status == WifiManager.STATUS_NETWORK_SUGGESTIONS_SUCCESS) {
                SuggestionResult.SUCCESS
            } else {
                SuggestionResult.SYSTEM_REJECTED
            }
        } catch (_: SecurityException) {
            SuggestionResult.PERMISSION_REQUIRED
        }
    }

    fun remove(profile: WifiProfile, wifiPsk: String?): SuggestionResult {
        val suggestion = buildSuggestion(profile, wifiPsk) ?: return SuggestionResult.INVALID_PSK
        return try {
            val status = wifiManager.removeNetworkSuggestions(listOf(suggestion))
            if (status == WifiManager.STATUS_NETWORK_SUGGESTIONS_SUCCESS) {
                SuggestionResult.SUCCESS
            } else {
                SuggestionResult.SYSTEM_REJECTED
            }
        } catch (_: SecurityException) {
            SuggestionResult.PERMISSION_REQUIRED
        }
    }

    private fun buildSuggestion(profile: WifiProfile, wifiPsk: String?): WifiNetworkSuggestion? {
        val builder = WifiNetworkSuggestion.Builder()
            .setSsid(profile.ssid)
            .setIsAppInteractionRequired(true)
        if (!wifiPsk.isNullOrBlank()) {
            if (wifiPsk.length !in 8..63) return null
            builder.setWpa2Passphrase(wifiPsk)
        }
        return builder.build()
    }
}
