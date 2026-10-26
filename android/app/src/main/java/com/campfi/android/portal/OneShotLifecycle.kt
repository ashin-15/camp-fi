package com.campfi.android.portal

/** Ensures a temporary login execution always releases its worker/service resources. */
class OneShotLifecycle(private val onShutdown: () -> Unit) {
    suspend fun <T> run(block: suspend () -> T): T = try {
        block()
    } finally {
        onShutdown()
    }
}
