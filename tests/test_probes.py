from camp_fi.net.probes import check_connectivity, ConnectivityStatus, ProbeSpec

def test_probe_success(monkeypatch):
    class FakeResponse:
        status_code = 204
        text = ""
        headers = {}

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
        status_code = 302
        text = ""
        headers = {"location": "http://portal.local/login"}

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
