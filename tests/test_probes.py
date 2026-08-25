import httpx

from camp_fi.net.probes import (
    PROBE_URLS,
    ConnectivityStatus,
    ProbeSpec,
    check_connectivity,
)


def test_probe_success(monkeypatch):
    class FakeResponse:
        def __init__(self):
            self.status_code = 204
            self.text = ""
            self.headers = {}

    class FakeClient:
        def __enter__(self):
            return self
        def __exit__(self, *args):
            pass
        def get(self, url):
            return FakeResponse()

    monkeypatch.setattr("camp_fi.net.probes.build_http_client", lambda **kwargs: FakeClient())
    res = check_connectivity()
    assert res.status == ConnectivityStatus.INTERNET
    assert res.probe_name == "Google"

def test_probe_captive_redirect(monkeypatch):
    class FakeResponse:
        def __init__(self):
            self.status_code = 302
            self.text = ""
            self.headers = {"location": "http://portal.local/login"}

    class FakeClient:
        def __enter__(self):
            return self
        def __exit__(self, *args):
            pass
        def get(self, url):
            return FakeResponse()

    monkeypatch.setattr("camp_fi.net.probes.build_http_client", lambda **kwargs: FakeClient())
    res = check_connectivity()
    assert res.status == ConnectivityStatus.CAPTIVE
    assert res.redirect_url == "http://portal.local/login"



def _make_client(handler):
    class FakeClient:
        def __enter__(self):
            return self
        def __exit__(self, *args):
            pass
        def get(self, url):
            return handler(url)
    return FakeClient()

def _unexpected_response():
    class ErrorResponse:
        def __init__(self):
            self.status_code = 403
            self.text = "blocked"
            self.headers = {}

    return ErrorResponse()

def _success_response():
    class SuccessResponse:
        def __init__(self):
            self.status_code = 204
            self.text = ""
            self.headers = {}

    return SuccessResponse()

def _two_spec_client(*, first_error: bool = False, second_success: bool = False):
    def handler(url):
        if url == PROBE_URLS[0] and first_error:
            raise httpx.ConnectTimeout("probe timed out")
        if url == PROBE_URLS[1] and second_success:
            return _success_response()
        return _unexpected_response()

    return _make_client(handler)

def _specs():
    return [
        ProbeSpec("Google", PROBE_URLS[0], 204),
        ProbeSpec("Cloudflare", PROBE_URLS[1], 204),
    ]

def test_one_flaky_probe_still_reports_internet(monkeypatch):
    monkeypatch.setattr(
        "camp_fi.net.probes.build_http_client",
        lambda **kwargs: _two_spec_client(first_error=True, second_success=True),
    )
    res = check_connectivity(specs=_specs())
    assert res.status == ConnectivityStatus.INTERNET
    assert res.probe_name == "Cloudflare"

def test_two_unexpected_responses_report_captive(monkeypatch):
    monkeypatch.setattr(
        "camp_fi.net.probes.build_http_client",
        lambda **kwargs: _two_spec_client(),
    )
    res = check_connectivity(specs=_specs())
    assert res.status == ConnectivityStatus.CAPTIVE
    assert res.status_code == 403

def test_one_error_one_unexpected_is_unknown(monkeypatch):
    monkeypatch.setattr(
        "camp_fi.net.probes.build_http_client",
        lambda **kwargs: _two_spec_client(first_error=True),
    )
    res = check_connectivity(specs=_specs())
    assert res.status == ConnectivityStatus.UNKNOWN
