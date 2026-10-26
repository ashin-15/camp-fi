package com.campfi.android.data

import android.content.Context
import android.util.Base64
import androidx.datastore.preferences.core.edit
import androidx.datastore.preferences.core.stringPreferencesKey
import androidx.datastore.preferences.preferencesDataStore
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.map
import kotlinx.coroutines.withContext
import java.nio.charset.StandardCharsets

private val Context.historyDataStore by preferencesDataStore(name = "login-history")

object Redactor {
    private val secretPattern = Regex("(?i)(password|passwd|pass|token|cookie|magic|csrf)=([^&\\s]+)")

    fun message(value: String): String = secretPattern.replace(value) { "${it.groupValues[1]}=[redacted]" }

    fun url(value: String): String = runCatching {
        java.net.URI(value).let { uri ->
            java.net.URI(uri.scheme, uri.authority, uri.path, null, null).toString()
        }
    }.getOrElse { "[redacted-url]" }
}

class LoginHistoryRepository(private val context: Context) {
    private val key = stringPreferencesKey("entries")
    private val maxEntries = 50

    val entries: Flow<List<LoginHistoryEntry>> = context.historyDataStore.data.map { preferences ->
        preferences[key].orEmpty().lineSequence().mapNotNull(::decode).toList()
    }

    suspend fun record(entry: LoginHistoryEntry) = withContext(Dispatchers.IO) {
        context.historyDataStore.edit { preferences ->
            val current = preferences[key].orEmpty().lineSequence().mapNotNull(::decode).toMutableList()
            current.add(
                entry.copy(
                    message = Redactor.message(entry.message),
                    adapterName = entry.adapterName?.take(40),
                ),
            )
            preferences[key] = current.takeLast(maxEntries).joinToString("\n", transform = ::encode)
        }
    }

    private fun encode(entry: LoginHistoryEntry): String = listOf(
        entry.timestamp.toString(),
        entry.profileId,
        entry.ssid,
        entry.status.name,
        entry.adapterName.orEmpty(),
        entry.message,
    ).joinToString("\t") { Base64.encodeToString(it.toByteArray(StandardCharsets.UTF_8), Base64.NO_WRAP) }

    private fun decode(line: String): LoginHistoryEntry? = runCatching {
        val values = line.split('\t').map {
            String(Base64.decode(it, Base64.NO_WRAP), StandardCharsets.UTF_8)
        }
        if (values.size != 6) return null
        LoginHistoryEntry(
            timestamp = values[0].toLong(),
            profileId = values[1],
            ssid = values[2],
            status = LoginStatus.valueOf(values[3]),
            adapterName = values[4].ifBlank { null },
            message = values[5],
        )
    }.getOrNull()
}
