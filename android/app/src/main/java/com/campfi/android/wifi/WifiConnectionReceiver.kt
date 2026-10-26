package com.campfi.android.wifi

import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.net.wifi.WifiManager
import android.net.wifi.WifiNetworkSuggestion
import android.os.Build
import com.campfi.android.service.LoginDispatch

class WifiConnectionReceiver : BroadcastReceiver() {
    override fun onReceive(context: Context, intent: Intent) {
        if (intent.action != WifiManager.ACTION_WIFI_NETWORK_SUGGESTION_POST_CONNECTION) return
        val suggestion = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
            intent.getParcelableExtra(WifiManager.EXTRA_NETWORK_SUGGESTION, WifiNetworkSuggestion::class.java)
        } else {
            @Suppress("DEPRECATION")
            intent.getParcelableExtra(WifiManager.EXTRA_NETWORK_SUGGESTION)
        } ?: return
        val ssid = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.R) {
            suggestion.ssid
        } else {
            @Suppress("DEPRECATION")
            context.getSystemService(WifiManager::class.java).connectionInfo?.ssid
        }?.trim('"')?.takeIf(String::isNotBlank) ?: return
        val gate = ConnectionEventGateStore.forContext(context)
        if (gate.accept(ssid)) LoginDispatch.enqueue(context, ssid)
    }
}

private object ConnectionEventGateStore {
    private val gates = mutableMapOf<String, ConnectionEventGate>()

    @Synchronized
    fun forContext(context: Context): ConnectionEventGate =
        gates.getOrPut(context.packageName) { ConnectionEventGate() }
}
