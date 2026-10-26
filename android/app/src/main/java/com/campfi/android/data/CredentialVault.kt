package com.campfi.android.data

import android.content.Context
import android.util.Base64
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import java.io.File
import java.nio.charset.StandardCharsets
import java.security.KeyStore
import javax.crypto.Cipher
import javax.crypto.KeyGenerator
import javax.crypto.SecretKey
import javax.crypto.spec.GCMParameterSpec
import javax.crypto.spec.SecretKeySpec

interface CredentialVault {
    suspend fun get(profileId: String): ProfileCredentials?
    suspend fun put(profileId: String, credentials: ProfileCredentials)
    suspend fun updateCookies(profileId: String, cookies: Map<String, String>)
    suspend fun delete(profileId: String)
}

/** AES/GCM encrypted vault. The key never leaves Android Keystore. */
class AndroidCredentialVault(private val context: Context) : CredentialVault {
    private val file: File get() = File(context.noBackupFilesDir, "credential-vault.bin")

    override suspend fun get(profileId: String): ProfileCredentials? = withContext(Dispatchers.IO) {
        readAll()[profileId]
    }

    override suspend fun put(profileId: String, credentials: ProfileCredentials) = withContext(Dispatchers.IO) {
        val values = readAll().toMutableMap()
        values[profileId] = credentials
        writeAll(values)
    }

    override suspend fun updateCookies(profileId: String, cookies: Map<String, String>) = withContext(Dispatchers.IO) {
        val current = readAll()[profileId] ?: return@withContext
        val values = readAll().toMutableMap()
        values[profileId] = current.copy(cookies = cookies)
        writeAll(values)
    }

    override suspend fun delete(profileId: String) = withContext(Dispatchers.IO) {
        val values = readAll().toMutableMap()
        values.remove(profileId)
        writeAll(values)
    }

    private fun readAll(): Map<String, ProfileCredentials> {
        if (!file.exists()) return emptyMap()
        val encrypted = file.readBytes()
        if (encrypted.size <= IV_SIZE) return emptyMap()
        val iv = encrypted.copyOfRange(0, IV_SIZE)
        val payload = encrypted.copyOfRange(IV_SIZE, encrypted.size)
        val cipher = Cipher.getInstance(TRANSFORMATION)
        cipher.init(Cipher.DECRYPT_MODE, key(), GCMParameterSpec(TAG_BITS, iv))
        val text = cipher.doFinal(payload).toString(StandardCharsets.UTF_8)
        return text.lineSequence()
            .filter(String::isNotBlank)
            .mapNotNull(::decodeLine)
            .toMap()
    }

    private fun writeAll(values: Map<String, ProfileCredentials>) {
        if (values.isEmpty()) {
            file.delete()
            return
        }
        val text = values.entries.joinToString("\n") { (id, credentials) ->
            listOf(
                id,
                credentials.username,
                credentials.password,
                credentials.wifiPsk.orEmpty(),
                credentials.cookies.entries.joinToString("\u001e") { "${it.key}\u001f${it.value}" },
            ).joinToString("\t", transform = ::encode)
        }
        val cipher = Cipher.getInstance(TRANSFORMATION)
        cipher.init(Cipher.ENCRYPT_MODE, key())
        val encrypted = cipher.doFinal(text.toByteArray(StandardCharsets.UTF_8))
        file.parentFile?.mkdirs()
        file.writeBytes(cipher.iv + encrypted)
    }

    private fun decodeLine(line: String): Pair<String, ProfileCredentials>? = runCatching {
        val values = line.split('\t').map { decode(it) }
        if (values.size < 5) return null
        val cookies = values[4].split('\u001e')
            .filter(String::isNotBlank)
            .mapNotNull { item ->
                val parts = item.split('\u001f', limit = 2)
                if (parts.size == 2) parts[0] to parts[1] else null
            }.toMap()
        values[0] to ProfileCredentials(values[1], values[2], values[3].ifBlank { null }, cookies)
    }.getOrNull()

    private fun encode(value: String): String = Base64.encodeToString(
        value.toByteArray(StandardCharsets.UTF_8),
        Base64.NO_WRAP,
    )

    private fun decode(value: String): String = String(
        Base64.decode(value, Base64.NO_WRAP),
        StandardCharsets.UTF_8,
    )

    private fun key(): SecretKey {
        val keyStore = KeyStore.getInstance(ANDROID_KEYSTORE).apply { load(null) }
        val existing = keyStore.getKey(KEY_ALIAS, null) as? SecretKey
        if (existing != null) return existing
        val generator = KeyGenerator.getInstance("AES", ANDROID_KEYSTORE)
        generator.init(
            android.security.keystore.KeyGenParameterSpec.Builder(
                KEY_ALIAS,
                android.security.keystore.KeyProperties.PURPOSE_ENCRYPT or
                    android.security.keystore.KeyProperties.PURPOSE_DECRYPT,
            ).setBlockModes(android.security.keystore.KeyProperties.BLOCK_MODE_GCM)
                .setEncryptionPaddings(android.security.keystore.KeyProperties.ENCRYPTION_PADDING_NONE)
                .setKeySize(256)
                .build(),
        )
        return generator.generateKey()
    }

    private companion object {
        const val ANDROID_KEYSTORE = "AndroidKeyStore"
        const val KEY_ALIAS = "camp-fi-credential-vault"
        const val TRANSFORMATION = "AES/GCM/NoPadding"
        const val IV_SIZE = 12
        const val TAG_BITS = 128
    }
}
