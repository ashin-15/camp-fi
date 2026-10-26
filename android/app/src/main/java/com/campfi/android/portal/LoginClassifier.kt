package com.campfi.android.portal

import com.campfi.android.data.LoginStatus

object LoginClassifier {
    fun fromHttpStatus(statusCode: Int): LoginStatus = when (statusCode) {
        401, 403 -> LoginStatus.AUTH_FAILED
        in 500..599 -> LoginStatus.NETWORK_ERROR
        in 200..399 -> LoginStatus.PROTOCOL_ERROR
        else -> LoginStatus.PROTOCOL_ERROR
    }

    fun verificationFailure(status: Int): LoginStatus = when (status) {
        401, 403 -> LoginStatus.AUTH_FAILED
        else -> LoginStatus.VERIFICATION_FAILED
    }
}
