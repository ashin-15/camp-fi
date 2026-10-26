package com.campfi.android.service

import android.app.Notification
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.Service
import android.content.Intent
import android.os.IBinder
import androidx.core.app.NotificationCompat
import com.campfi.android.R
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.Job
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.cancel
import kotlinx.coroutines.launch

class OneShotLoginService : Service() {
    private val serviceScope = CoroutineScope(SupervisorJob() + Dispatchers.IO)
    private var activeJob: Job? = null

    override fun onCreate() {
        super.onCreate()
        createChannel()
        startForeground(NOTIFICATION_ID, notification())
    }

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        if (activeJob?.isActive == true) return START_NOT_STICKY
        val ssid = intent?.getStringExtra(LoginDispatch.EXTRA_SSID)
        if (ssid.isNullOrBlank()) {
            stopSelf(startId)
            return START_NOT_STICKY
        }
        val portalUrl = intent.getStringExtra(LoginDispatch.EXTRA_PORTAL_URL)
        activeJob = serviceScope.launch {
            try {
                LoginOperation(this@OneShotLoginService).run(ssid, portalUrl)
            } finally {
                stopSelf(startId)
            }
        }
        return START_NOT_STICKY
    }

    override fun onDestroy() {
        activeJob?.cancel()
        serviceScope.cancel()
        super.onDestroy()
    }

    override fun onBind(intent: Intent?): IBinder? = null

    private fun createChannel() {
        getSystemService(NotificationManager::class.java).createNotificationChannel(
            NotificationChannel(CHANNEL_ID, getString(R.string.login_channel_name), NotificationManager.IMPORTANCE_LOW),
        )
    }

    private fun notification(): Notification = NotificationCompat.Builder(this, CHANNEL_ID)
        .setSmallIcon(android.R.drawable.stat_notify_sync)
        .setContentTitle(getString(R.string.login_notification_title))
        .setContentText(getString(R.string.login_notification_text))
        .setOngoing(true)
        .build()

    private companion object {
        const val CHANNEL_ID = "captive-portal-login"
        const val NOTIFICATION_ID = 1001
    }
}
