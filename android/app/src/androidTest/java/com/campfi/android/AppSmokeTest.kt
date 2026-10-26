package com.campfi.android

import androidx.test.ext.junit.runners.AndroidJUnit4
import androidx.test.platform.app.InstrumentationRegistry
import org.junit.Assert.assertEquals
import org.junit.Test
import org.junit.runner.RunWith

@RunWith(AndroidJUnit4::class)
class AppSmokeTest {
    @Test
    fun targetPackageIsInstalled() {
        val context = InstrumentationRegistry.getInstrumentation().targetContext
        assertEquals("com.campfi.android", context.packageName)
    }
}
