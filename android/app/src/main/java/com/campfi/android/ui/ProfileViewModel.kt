package com.campfi.android.ui

import android.app.Application
import androidx.lifecycle.AndroidViewModel
import androidx.lifecycle.viewModelScope
import com.campfi.android.data.AndroidCredentialVault
import com.campfi.android.data.DefaultPortalConfig
import com.campfi.android.data.ProfileCredentials
import com.campfi.android.data.ProfileRepository
import com.campfi.android.data.StatusRepository
import com.campfi.android.data.WifiProfile
import com.campfi.android.wifi.SuggestionResult
import com.campfi.android.wifi.WifiSuggestionManager
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.collect
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch
import java.util.UUID

data class ProfileUiState(
    val ssid: String = "",
    val username: String = "",
    val password: String = "",
    val profiles: List<WifiProfile> = emptyList(),
    val message: String = "",
    val isSaving: Boolean = false,
)

class ProfileViewModel(application: Application) : AndroidViewModel(application) {
    private val profileRepository = ProfileRepository(application)
    private val vault = AndroidCredentialVault(application)
    private val suggestionManager = WifiSuggestionManager(application)
    private val statusRepository = StatusRepository(application)
    private val _state = MutableStateFlow(ProfileUiState())
    val state: StateFlow<ProfileUiState> = _state.asStateFlow()
    val status = statusRepository.snapshot

    init {
        viewModelScope.launch {
            profileRepository.profiles.collect { profiles ->
                _state.update { it.copy(profiles = profiles) }
            }
        }
    }

    fun setSsid(value: String) = _state.update { it.copy(ssid = value, message = "") }
    fun setUsername(value: String) = _state.update { it.copy(username = value, message = "") }
    fun setPassword(value: String) = _state.update { it.copy(password = value, message = "") }

    fun save() {
        val current = _state.value
        if (current.ssid.isBlank() || current.username.isBlank() || current.password.isBlank()) {
            _state.update { it.copy(message = "SSID, portal username, and portal password are required.") }
            return
        }
        viewModelScope.launch {
            _state.update { it.copy(isSaving = true, message = "Saving encrypted credentials…") }
            val id = UUID.randomUUID().toString()
            val profile = WifiProfile(
                id = id,
                ssid = current.ssid.trim(),
                adapterType = DefaultPortalConfig.adapterType,
                approvedHosts = DefaultPortalConfig.approvedHosts,
                enabled = true,
            )
            vault.put(id, ProfileCredentials(current.username.trim(), current.password))
            profileRepository.save(profile)
            val registration = suggestionManager.register(profile, wifiPsk = null)
            val message = when (registration) {
                SuggestionResult.SUCCESS -> "Profile saved. Android will connect and trigger one-shot login."
                SuggestionResult.PERMISSION_REQUIRED -> "Profile saved. Grant Wi-Fi/location permissions to register the suggestion."
                SuggestionResult.INVALID_PSK -> "The Wi-Fi suggestion could not be created."
                SuggestionResult.SYSTEM_REJECTED -> "Profile saved, but Android rejected the Wi-Fi suggestion."
            }
            _state.update {
                it.copy(ssid = "", username = "", password = "", isSaving = false, message = message)
            }
        }
    }

    fun delete(profile: WifiProfile) {
        viewModelScope.launch {
            suggestionManager.remove(profile, wifiPsk = null)
            vault.delete(profile.id)
            profileRepository.delete(profile.id)
            _state.update { it.copy(message = "Removed ${profile.ssid}.") }
        }
    }
}
