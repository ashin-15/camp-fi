package com.campfi.android.service

import android.content.Context
import android.content.Intent
import androidx.work.CoroutineWorker
import androidx.work.ExistingWorkPolicy
import androidx.work.OneTimeWorkRequestBuilder
import androidx.work.OutOfQuotaPolicy
import androidx.work.WorkManager
import androidx.work.WorkerParameters

object LoginDispatch {
    const val EXTRA_SSID = "com.campfi.android.extra.SSID"
    const val EXTRA_PROFILE_ID = "com.campfi.android.extra.PROFILE_ID"
    const val EXTRA_PORTAL_URL = "com.campfi.android.extra.PORTAL_URL"

    fun enqueue(context: Context, ssid: String, portalUrl: String? = null) {
        val intent = Intent(context, OneShotLoginService::class.java)
            .putExtra(EXTRA_SSID, ssid)
            .apply { portalUrl?.let { putExtra(EXTRA_PORTAL_URL, it) } }
        try {
            context.startForegroundService(intent)
        } catch (_: IllegalStateException) {
            enqueueWorker(context, ssid, portalUrl)
        } catch (_: SecurityException) {
            enqueueWorker(context, ssid, portalUrl)
        }
    }

    fun enqueueWorker(context: Context, ssid: String, portalUrl: String? = null) {
        val request = OneTimeWorkRequestBuilder<OneShotLoginWorker>()
            .setInputData(androidx.work.workDataOf(EXTRA_SSID to ssid, EXTRA_PORTAL_URL to portalUrl))
            .setExpedited(OutOfQuotaPolicy.RUN_AS_NON_EXPEDITED_WORK_REQUEST)
            .build()
        WorkManager.getInstance(context).enqueueUniqueWork(
            "one-shot-login-$ssid",
            ExistingWorkPolicy.KEEP,
            request,
        )
    }
}

class OneShotLoginWorker(appContext: Context, params: WorkerParameters) : CoroutineWorker(appContext, params) {
    override suspend fun doWork(): Result {
        LoginOperation(applicationContext).run(
            inputData.getString(LoginDispatch.EXTRA_SSID) ?: return Result.failure(),
            inputData.getString(LoginDispatch.EXTRA_PORTAL_URL),
        )
        return Result.success()
    }
}
