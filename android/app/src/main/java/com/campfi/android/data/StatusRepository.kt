package com.campfi.android.data

import android.content.Context
import androidx.datastore.preferences.core.edit
import androidx.datastore.preferences.core.stringPreferencesKey
import androidx.datastore.preferences.preferencesDataStore
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.map

private val Context.statusDataStore by preferencesDataStore(name = "status")

class StatusRepository(private val context: Context) {
    private val timestampKey = stringPreferencesKey("timestamp")
    private val profileKey = stringPreferencesKey("profile")
    private val ssidKey = stringPreferencesKey("ssid")
    private val statusKey = stringPreferencesKey("status")
    private val messageKey = stringPreferencesKey("message")

    val snapshot: Flow<StatusSnapshot> = context.statusDataStore.data.map { preferences ->
        StatusSnapshot(
            timestamp = preferences[timestampKey]?.toLongOrNull() ?: 0L,
            profileId = preferences[profileKey],
            ssid = preferences[ssidKey],
            status = preferences[statusKey]?.let { runCatching { LoginStatus.valueOf(it) }.getOrNull() },
            message = preferences[messageKey] ?: "Waiting for a configured Wi-Fi connection.",
        )
    }

    suspend fun update(profile: WifiProfile, result: LoginResult, now: Long = System.currentTimeMillis()) {
        context.statusDataStore.edit { preferences ->
            preferences[timestampKey] = now.toString()
            preferences[profileKey] = profile.id
            preferences[ssidKey] = profile.ssid
            preferences[statusKey] = result.status.name
            preferences[messageKey] = Redactor.message(result.message).take(240)
        }
    }
}
