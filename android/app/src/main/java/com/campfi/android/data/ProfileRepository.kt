package com.campfi.android.data

import android.content.Context
import androidx.datastore.preferences.core.Preferences
import androidx.datastore.preferences.core.edit
import androidx.datastore.preferences.core.stringSetPreferencesKey
import androidx.datastore.preferences.core.stringPreferencesKey
import androidx.datastore.preferences.preferencesDataStore
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.flow.map

private val Context.profileDataStore by preferencesDataStore(name = "profiles")

/** Stores only non-secret profile metadata. Credentials are kept in CredentialVault. */
class ProfileRepository(private val context: Context) {
    private val idsKey = stringSetPreferencesKey("profile_ids")

    val profiles: Flow<List<WifiProfile>> = context.profileDataStore.data.map { preferences ->
        preferences[idsKey].orEmpty().mapNotNull { id -> readProfile(preferences, id) }
            .sortedBy { it.ssid.lowercase() }
    }

    suspend fun get(id: String): WifiProfile? = profiles.first().firstOrNull { it.id == id }

    suspend fun findEnabledBySsid(ssid: String): WifiProfile? = profiles.first().firstOrNull {
        it.enabled && it.ssid == ssid
    }

    suspend fun save(profile: WifiProfile) {
        context.profileDataStore.edit { preferences ->
            val ids = preferences[idsKey].orEmpty() + profile.id
            preferences[idsKey] = ids
            preferences[key(profile.id, "ssid")] = profile.ssid
            preferences[key(profile.id, "adapter")] = profile.adapterType.name
            preferences[key(profile.id, "hosts")] = profile.approvedHosts
                .map(::normalizeHost)
                .filter(String::isNotBlank)
                .distinct()
                .sorted()
                .joinToString("\n")
            preferences[key(profile.id, "enabled")] = profile.enabled.toString()
        }
    }

    suspend fun delete(id: String) {
        context.profileDataStore.edit { preferences ->
            preferences[idsKey] = preferences[idsKey].orEmpty() - id
            listOf("ssid", "adapter", "hosts", "enabled").forEach { suffix ->
                preferences.remove(key(id, suffix))
            }
        }
    }

    private fun readProfile(preferences: Preferences, id: String): WifiProfile? {
        val ssid = preferences[key(id, "ssid")] ?: return null
        val adapter = preferences[key(id, "adapter")]
            ?.let { runCatching { PortalAdapterType.valueOf(it) }.getOrNull() }
            ?: PortalAdapterType.AUTO
        val hosts = preferences[key(id, "hosts")]
            .orEmpty()
            .split('\n')
            .map(::normalizeHost)
            .filter(String::isNotBlank)
            .toSet()
        return WifiProfile(
            id = id,
            ssid = ssid,
            adapterType = adapter,
            approvedHosts = hosts,
            enabled = preferences[key(id, "enabled")]?.toBoolean() ?: true,
        )
    }

    private fun key(id: String, suffix: String) = stringPreferencesKey("profile_${id}_$suffix")
}
