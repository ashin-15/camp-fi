package com.campfi.android.portal

import kotlinx.coroutines.delay

data class RetryConfig(
    val maxAttempts: Int = 3,
    val initialDelayMs: Long = 750L,
    val maxDelayMs: Long = 8_000L,
)

class RetryPolicy(
    private val config: RetryConfig = RetryConfig(),
    private val sleeper: suspend (Long) -> Unit = { delay(it) },
) {
    suspend fun <T> execute(
        operation: suspend (attempt: Int) -> T,
        shouldRetry: (T) -> Boolean,
    ): RetryOutcome<T> {
        val attempts = config.maxAttempts.coerceAtLeast(1)
        var last: T? = null
        repeat(attempts) { index ->
            val value = operation(index + 1)
            last = value
            if (!shouldRetry(value) || index == attempts - 1) {
                return RetryOutcome(value, index + 1)
            }
            val backoff = (config.initialDelayMs * (1L shl index.coerceAtMost(20)))
                .coerceAtMost(config.maxDelayMs)
            sleeper(backoff)
        }
        @Suppress("UNCHECKED_CAST")
        return RetryOutcome(last as T, attempts)
    }
}

data class RetryOutcome<T>(val value: T, val attempts: Int)
