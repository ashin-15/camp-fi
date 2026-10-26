package com.campfi.android.portal

import org.junit.Assert.assertEquals
import org.junit.Assert.assertNotNull
import org.junit.Assert.assertTrue
import org.junit.Test

class HtmlFormParserTest {
    @Test
    fun parsesHiddenCsrfRelativePostActionAndCheckedControls() {
        val form = HtmlFormParser.parse(
            """
            <form action="/auth?next=home" method="post">
              <input type="hidden" name="csrf" value="abc&amp;123">
              <input type="text" name="student_user">
              <input type="password" name="secret">
              <input type="checkbox" name="terms" value="yes" checked>
              <input type="checkbox" name="ignored" value="no">
              <button type="submit" name="submit" value="Sign in">Login</button>
            </form>
            """.trimIndent(),
            "https://portal.example/login/index.html",
        )

        assertNotNull(form)
        requireNotNull(form)
        assertEquals("https://portal.example/auth?next=home", form.action)
        assertEquals("POST", form.method)
        assertEquals("abc&123", form.fields["csrf"])
        assertEquals("yes", form.fields["terms"])
        assertTrue("ignored" !in form.fields)
        assertEquals("Sign in", form.fields["submit"])
        assertEquals("student_user", form.usernameField)
        assertEquals("secret", form.passwordField)
    }

    @Test
    fun supportsGetFormsAndChoosesTheFirstLoginFormAmongMultipleForms() {
        val form = HtmlFormParser.parse(
            """
            <form action="/search" method="get"><input name="q"></form>
            <form action="authenticate"><input type="email" name="email"><input type="password" name="password"></form>
            """.trimIndent(),
            "https://portal.example/start",
        )

        requireNotNull(form)
        assertEquals("https://portal.example/authenticate", form.action)
        assertEquals("GET", form.method)
        assertEquals("email", form.usernameField)
        assertEquals("password", form.passwordField)
    }

    @Test
    fun formEncodingPreservesSpacesAndReservedCharacters() {
        assertEquals("user=a+b%2Bc%40example.com", HtmlFormParser.encode(mapOf("user" to "a b+c@example.com")))
    }
}
