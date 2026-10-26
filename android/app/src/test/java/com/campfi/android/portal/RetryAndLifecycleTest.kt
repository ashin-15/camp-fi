package com.campfi.android.portal

import com.campfi.android.data.LoginStatus
import kotlinx.coroutines.runBlocking
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

class RetryAndLifecycleTest {
    @Test
    fun retriesWithCappedExponentialBackoff() = runBlocking {
        val delays = mutableListOf<Long>()
        var attempts = 0
        val outcome = RetryPolicy(
            RetryConfig(maxAttempts = 4, initialDelayMs = 10, maxDelayMs = 15),
            sleeper = { delays += it },
        ).execute(
            operation = {
                attempts += 1
                if (attempts < 4) LoginStatus.NETWORK_ERROR else LoginStatus.SUCCESS
            },
            shouldRetry = { it == LoginStatus.NETWORK_ERROR },
        )
        assertEquals(LoginStatus.SUCCESS, outcome.value)
        assertEquals(4, outcome.attempts)
        assertEquals(listOf(10L, 15L, 15L), delays)
    }

    @Test
    fun oneShotShutdownRunsAfterSuccessAndFailure() = runBlocking {
        var shutdowns = 0
        val lifecycle = OneShotLifecycle { shutdowns += 1 }
        assertEquals("ok", lifecycle.run { "ok" })
        assertEquals(1, shutdowns)
        runCatching { lifecycle.run<String> { error("failed") } }
        assertEquals(2, shutdowns)
    }

    @Test
    fun duplicateConnectionEventsAreSuppressedWithinWindow() {
        var now = 1_000L
        val gate = com.campfi.android.wifi.ConnectionEventGate({ now }, suppressionWindowMs = 30_000L)
        assertTrue(gate.accept("IIITKottayam_5G"))
        assertTrue(!gate.accept("IIITKottayam_5G"))
        now += 30_001L
        assertTrue(gate.accept("IIITKottayam_5G"))
    }
}
