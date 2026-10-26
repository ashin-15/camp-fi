package com.campfi.android.ui

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.text.input.PasswordVisualTransformation
import androidx.compose.ui.unit.dp
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.campfi.android.data.StatusSnapshot

@Composable
fun ProfileScreen(viewModel: ProfileViewModel, onSave: () -> Unit) {
    val state by viewModel.state.collectAsStateWithLifecycle()
    val status by viewModel.status.collectAsStateWithLifecycle(initialValue = StatusSnapshot())
    Surface(modifier = Modifier.fillMaxSize()) {
        Column(
            modifier = Modifier
                .fillMaxSize()
                .verticalScroll(rememberScrollState())
                .padding(20.dp),
            verticalArrangement = Arrangement.spacedBy(12.dp),
        ) {
            Text("camp-fi Android", style = MaterialTheme.typography.headlineMedium)
            Text(
                "Add a Wi-Fi profile once. Android will connect to the open network and run one captive-portal login when it reports a connection.",
                style = MaterialTheme.typography.bodyMedium,
            )
            ProfileForm(state, viewModel, onSave)
            AddedProfiles(state, viewModel)
            StatusCard(status)
        }
    }
}

@Composable
private fun ProfileForm(state: ProfileUiState, viewModel: ProfileViewModel, onSave: () -> Unit) {
    OutlinedTextField(
        value = state.ssid,
        onValueChange = viewModel::setSsid,
        label = { Text("Wi-Fi SSID") },
        placeholder = { Text("IIITKottayam_5G") },
        singleLine = true,
        modifier = Modifier.fillMaxWidth(),
    )
    OutlinedTextField(
        value = state.username,
        onValueChange = viewModel::setUsername,
        label = { Text("Portal username") },
        singleLine = true,
        modifier = Modifier.fillMaxWidth(),
    )
    OutlinedTextField(
        value = state.password,
        onValueChange = viewModel::setPassword,
        label = { Text("Portal password") },
        singleLine = true,
        visualTransformation = PasswordVisualTransformation(),
        keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Password),
        modifier = Modifier.fillMaxWidth(),
    )
    Button(onClick = onSave, enabled = !state.isSaving, modifier = Modifier.fillMaxWidth()) {
        Text(if (state.isSaving) "Saving…" else "Save profile")
    }
    if (state.message.isNotBlank()) {
        Text(state.message, color = MaterialTheme.colorScheme.primary)
    }
    Text(
        "The app uses automatic portal detection and the built-in approved IIITK portal policy. No continuous scanning, polling, periodic login, or keepalive timer is used.",
        style = MaterialTheme.typography.bodySmall,
    )
}

@Composable
private fun AddedProfiles(state: ProfileUiState, viewModel: ProfileViewModel) {
    Card(modifier = Modifier.fillMaxWidth()) {
        Column(modifier = Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
            Text("Added profiles", style = MaterialTheme.typography.titleMedium)
            if (state.profiles.isEmpty()) {
                Text("No profiles saved yet.", style = MaterialTheme.typography.bodyMedium)
            } else {
                state.profiles.forEach { profile ->
                    Row(modifier = Modifier.fillMaxWidth()) {
                        Text(profile.ssid, modifier = Modifier.weight(1f))
                        IconButton(onClick = { viewModel.delete(profile) }) {
                            Text("×", style = MaterialTheme.typography.titleLarge)
                        }
                    }
                }
            }
        }
    }
}

@Composable
private fun StatusCard(status: StatusSnapshot) {
    Card(modifier = Modifier.fillMaxWidth()) {
        Column(modifier = Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(6.dp)) {
            Text("Latest status", style = MaterialTheme.typography.titleMedium)
            Text(status.status?.name ?: "WAITING")
            Text(status.message, style = MaterialTheme.typography.bodyMedium)
            status.ssid?.let { Text("SSID: $it", style = MaterialTheme.typography.bodySmall) }
        }
    }
}
