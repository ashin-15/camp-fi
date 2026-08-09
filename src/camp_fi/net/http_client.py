import ssl
import httpx

def build_http_client(
    *,
    timeout: float | httpx.Timeout = 10.0,
    follow_redirects: bool = True,
    verify: bool | str | ssl.SSLContext = True,
) -> httpx.Client:
    """Centralized HTTP client factory with secure defaults (TLS verification enabled)."""
    return httpx.Client(
        timeout=timeout,
        follow_redirects=follow_redirects,
        verify=verify,
    )
