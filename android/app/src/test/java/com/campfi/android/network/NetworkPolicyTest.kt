package com.campfi.android.network

import com.campfi.android.data.LoginStatus
import com.campfi.android.portal.LoginClassifier
import com.campfi.android.portal.ManualFallbackPolicy
import com.campfi.android.data.LoginResult
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test
import java.net.URL

class NetworkPolicyTest {
    @Test
    fun allowsApprovedHostAndSubdomainsButRejectsLookalikes() {
        val policy = ApprovedHostPolicy(setOf("auth.example.com"))
        assertTrue(policy.isAllowed("https://auth.example.com/login"))
        assertTrue(policy.isAllowed("https://login.auth.example.com/start"))
        assertFalse(policy.isAllowed("https://auth.example.com.attacker.test/login"))
        assertFalse(policy.isAllowed("https://other.example.com/login"))
    }

    @Test
    fun probeClassifiesNetworkBoundResponses() {
        val seen = mutableListOf<URL>()
        val transport = ProbeTransport { url ->
            seen += url
            ProbeResponse(204)
        }
        val result = NetworkProbe(transport).check()
        assertEquals(ConnectivityStatus.INTERNET, result.status)
        assertEquals(1, seen.size)
    }

    @Test
    fun redirectNavigatorIsBounded() {
        val navigator = RedirectNavigator(3)
        assertTrue(navigator.canFollow(0))
        assertTrue(navigator.canFollow(2))
        assertFalse(navigator.canFollow(3))
        assertEquals("https://portal.example/next", HtmlRedirectParser.next(
            "<meta http-equiv=\"refresh\" content=\"0;url=/next\">",
            "https://portal.example/start",
        ))
    }

    @Test
    fun resultClassificationAndUnsupportedFallbackAreStable() {
        assertEquals(LoginStatus.AUTH_FAILED, LoginClassifier.fromHttpStatus(401))
        assertEquals(LoginStatus.VERIFICATION_FAILED, LoginClassifier.verificationFailure(204))
        assertTrue(ManualFallbackPolicy.shouldOffer(LoginResult(LoginStatus.UNSUPPORTED_PORTAL)))
        assertFalse(ManualFallbackPolicy.shouldOffer(LoginResult(LoginStatus.AUTH_FAILED)))
    }
}
