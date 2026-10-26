package com.campfi.android

import android.Manifest
import android.content.Intent
import android.content.pm.PackageManager
import android.net.Uri
import android.os.Build
import android.os.Bundle
import android.provider.Settings
import android.widget.Toast
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.result.contract.ActivityResultContracts
import androidx.core.content.ContextCompat
import androidx.lifecycle.ViewModelProvider
import com.campfi.android.ui.ProfileScreen
import com.campfi.android.ui.ProfileViewModel

class MainActivity : ComponentActivity() {
    private var saveAfterPermission = false
    private lateinit var profileViewModel: ProfileViewModel

    private val wifiPermissionLauncher = registerForActivityResult(
        ActivityResultContracts.RequestMultiplePermissions(),
    ) { results ->
        val granted = results[Manifest.permission.ACCESS_FINE_LOCATION] == true &&
            (Build.VERSION.SDK_INT < Build.VERSION_CODES.TIRAMISU ||
                results[Manifest.permission.NEARBY_WIFI_DEVICES] == true ||
                ContextCompat.checkSelfPermission(this, Manifest.permission.NEARBY_WIFI_DEVICES) == PackageManager.PERMISSION_GRANTED)
        if (granted && saveAfterPermission) {
            profileViewModel.save()
        } else if (!granted) {
            Toast.makeText(this, "Wi-Fi permissions are required for connection events.", Toast.LENGTH_LONG).show()
            if (!shouldShowRequestPermissionRationale(Manifest.permission.ACCESS_FINE_LOCATION)) {
                startActivity(Intent(Settings.ACTION_APPLICATION_DETAILS_SETTINGS).apply {
                    data = Uri.fromParts("package", packageName, null)
                })
            }
        }
        saveAfterPermission = false
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        profileViewModel = ViewModelProvider(this)[ProfileViewModel::class.java]
        setContent {
            CampFiTheme {
                ProfileScreen(
                    viewModel = profileViewModel,
                    onSave = {
                        saveAfterPermission = true
                        if (hasWifiPermissions()) profileViewModel.save() else requestWifiPermissions()
                    },
                )
            }
        }
    }

    private fun hasWifiPermissions(): Boolean {
        val locationGranted = ContextCompat.checkSelfPermission(
            this,
            Manifest.permission.ACCESS_FINE_LOCATION,
        ) == PackageManager.PERMISSION_GRANTED
        val nearbyGranted = Build.VERSION.SDK_INT < Build.VERSION_CODES.TIRAMISU ||
            ContextCompat.checkSelfPermission(this, Manifest.permission.NEARBY_WIFI_DEVICES) == PackageManager.PERMISSION_GRANTED
        return locationGranted && nearbyGranted
    }

    private fun requestWifiPermissions() {
        val permissions = buildList {
            if (ContextCompat.checkSelfPermission(this@MainActivity, Manifest.permission.ACCESS_FINE_LOCATION) != PackageManager.PERMISSION_GRANTED) {
                add(Manifest.permission.ACCESS_FINE_LOCATION)
            }
            if (ContextCompat.checkSelfPermission(this@MainActivity, Manifest.permission.ACCESS_COARSE_LOCATION) != PackageManager.PERMISSION_GRANTED) {
                add(Manifest.permission.ACCESS_COARSE_LOCATION)
            }
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU &&
                ContextCompat.checkSelfPermission(this@MainActivity, Manifest.permission.NEARBY_WIFI_DEVICES) != PackageManager.PERMISSION_GRANTED
            ) {
                add(Manifest.permission.NEARBY_WIFI_DEVICES)
            }
        }
        if (permissions.isNotEmpty()) wifiPermissionLauncher.launch(permissions.toTypedArray())
    }
}
