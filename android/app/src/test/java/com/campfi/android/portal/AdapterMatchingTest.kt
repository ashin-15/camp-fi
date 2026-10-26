package com.campfi.android.portal

import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class AdapterMatchingTest {
    @Test
    fun iiitkAdapterMatchesKnownHostOrPageMarker() {
        val adapter = IIITKAdapter()
        assertTrue(adapter.matches("<html></html>", "https://auth.iiitkottayam.ac.in/login"))
        assertTrue(adapter.matches("auth.iiitkottayam.ac.in", "http://192.0.2.1/"))
        assertFalse(adapter.matches("<html></html>", "https://example.com/login"))
    }

    @Test
    fun fortinetAdapterRequiresMagicAndFortinetSignal() {
        val adapter = FortinetAdapter()
        assertTrue(adapter.matches("<input name=\"magic\" value=\"abc\">fgtauth", "http://192.0.2.1:1000/login"))
        assertFalse(adapter.matches("<input name=\"magic\" value=\"abc\">", "https://example.com/login"))
        assertFalse(adapter.matches("fortinet", "https://example.com/login"))
    }

    @Test
    fun genericAdapterRequiresPasswordForm() {
        val adapter = GenericFormAdapter()
        assertTrue(adapter.matches("<form><input name=user><input type=password name=pass></form>", "https://portal.example/"))
        assertFalse(adapter.matches("<form><input name=user></form>", "https://portal.example/"))
    }
}
