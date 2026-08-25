import pytest
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
import time
import httpx
from urllib.parse import parse_qs
from camp_fi.net.captive import execute_login
from camp_fi.net.probes import check_connectivity
from camp_fi.keepalive import parse_js_keepalive, parse_keepalive, KeepaliveInfo
import json
import logging

PORT = 8080

DEVICE_LOGGED_IN = False

class FakePortalHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        global DEVICE_LOGGED_IN
        if self.path == "/generate_204":
            if "session=logged_in" in self.headers.get("Cookie", "") or DEVICE_LOGGED_IN:
                self.send_response(204)
                self.end_headers()
            else:
                self.send_response(302)
                self.send_header("Location", f"http://127.0.0.1:{PORT}/login")
                self.end_headers()
            
        elif self.path == "/login":
            self.send_response(200)
            self.send_header("Content-type", "text/html")
            self.end_headers()
            self.wfile.write(b"""
            <html>
                <body>
                    <form action="/auth" method="POST">
                        <input type="hidden" name="csrf" value="12345">
                        <input type="text" name="username">
                        <input type="password" name="password">
                    </form>
                </body>
            </html>
            """)
            
        elif self.path == "/keepalive":
            self.send_response(200)
            self.send_header("Content-type", "text/html")
            self.end_headers()
            self.wfile.write(b"""
            <html>
                <head>
                    <meta http-equiv="refresh" content="300;url=/keepalive">
                </head>
                <body>Keepalive</body>
            </html>
            """)
        elif self.path == "/login-js":
            self.send_response(200)
            self.send_header("Content-type", "text/html")
            self.end_headers()
            self.wfile.write(b"""
            <html>
                <body>
                    <form action="/auth-js" method="POST">
                        <input type="text" name="username">
                        <input type="password" name="password">
                    </form>
                </body>
            </html>
            """)
        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        global DEVICE_LOGGED_IN
        if self.path == "/auth":
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            params = parse_qs(post_data.decode('utf-8'))
            
            if params.get('username', [''])[0] == 'testuser' and params.get('password', [''])[0] == 'testpass':
                DEVICE_LOGGED_IN = True
                self.send_response(200)
                self.send_header("Set-Cookie", "session=logged_in; Path=/")
                self.send_header("Content-type", "text/html")
                self.end_headers()
                self.wfile.write(b"""
                <html>
                    <head>
                        <meta http-equiv="refresh" content="300;url=/keepalive">
                    </head>
                    <body>Success</body>
                </html>
                """)
            else:
                self.send_response(401)
                self.end_headers()
        elif self.path == "/auth-js":
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            params = parse_qs(post_data.decode('utf-8'))
            
            if params.get('username', [''])[0] == 'testuser' and params.get('password', [''])[0] == 'testpass':
                DEVICE_LOGGED_IN = True
                self.send_response(200)
                self.send_header("Set-Cookie", "session=logged_in; Path=/")
                self.send_header("Content-type", "text/html")
                self.end_headers()
                self.wfile.write(b"""
                <html>
                    <head>
                        <script>
                            setInterval(function() {
                                fetch('/keepalive?session=abc1234');
                            }, 180000);
                        </script>
                    </head>
                    <body>Success JS Keepalive</body>
                </html>
                """)
            else:
                self.send_response(401)
                self.end_headers()
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, format, *args):
        pass

def start_server():
    server = HTTPServer(("127.0.0.1", PORT), FakePortalHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server

@pytest.fixture(scope="module")
def fake_server():
    server = start_server()
    time.sleep(0.5)
    yield server
    server.shutdown()
    global DEVICE_LOGGED_IN
    DEVICE_LOGGED_IN = False

def test_fake_portal_login(fake_server, monkeypatch, tmp_path):
    # Setup paths
    monkeypatch.setattr("camp_fi.paths.get_state_dir", lambda: tmp_path)
    monkeypatch.setattr("camp_fi.paths.get_config_dir", lambda: tmp_path)
    
    # Monkeypatch PROBE_URLS to local server
    monkeypatch.setattr("camp_fi.net.probes.PROBE_URLS", [f"http://127.0.0.1:{PORT}/generate_204"])
    
    # 1. Initial connectivity check
    probe = check_connectivity(timeout=1.0)
    assert probe.status.name == "CAPTIVE"
    assert probe.redirect_url == f"http://127.0.0.1:{PORT}/login"
    
    # 2. Execute login
    cookies_path = tmp_path / "cookies-test.json"
    result = execute_login(
        redirect_url=probe.redirect_url,
        username="testuser",
        password="testpass",
        cookies_path=cookies_path
    )
    
    assert result.succeeded is True
    assert result.adapter_name == "generic_form"
    assert result.keepalive is not None
    assert result.keepalive.interval_seconds == 300
    assert cookies_path.exists()
    with cookies_path.open("r") as f:
        cookies = json.load(f)
        assert any(c.get("name") == "session" and c.get("value") == "logged_in" for c in cookies)

def test_fake_portal_js_keepalive_login(fake_server, monkeypatch, tmp_path):
    monkeypatch.setattr("camp_fi.paths.get_state_dir", lambda: tmp_path)
    monkeypatch.setattr("camp_fi.paths.get_config_dir", lambda: tmp_path)

    cookies_path = tmp_path / "cookies-js-test.json"
    result = execute_login(
        redirect_url=f"http://127.0.0.1:{PORT}/login-js",
        username="testuser",
        password="testpass",
        cookies_path=cookies_path,
    )

    assert result.succeeded is True
    assert result.adapter_name == "generic_form"
    assert result.keepalive is not None
    assert result.keepalive.url == f"http://127.0.0.1:{PORT}/keepalive?session=abc1234"
    assert result.keepalive.interval_seconds == 180


@pytest.mark.parametrize(
    "html,base_url,expected_url,expected_interval",
    [
        (
            """
            <html>
            <script>
                setInterval(function() {
                    fetch('/keepalive');
                }, 300000);
            </script>
            </html>
            """,
            "http://192.168.1.1/portal",
            "http://192.168.1.1/keepalive",
            300,
        ),
        (
            """
            <script>
                setInterval(() => {
                    fetch('/ping?token=xyz');
                }, 60000);
            """,
            "https://auth.example.com/login/",
            "https://auth.example.com/ping?token=xyz",
            60,
        ),
        (
            """
            <script>
                setInterval(() => {
                    fetch('ping?token=xyz');
                }, 60000);
            </script>
            """,
            "https://auth.example.com/login/",
            "https://auth.example.com/login/ping?token=xyz",
            60,
        ),
        (
            """
            <script>
                setInterval(function() {
                    var xhr = new XMLHttpRequest();
                    xhr.open("GET", "/keepalive", true);
                    xhr.send();
                }, 120000);
            </script>
            """,
            "http://10.0.0.1/",
            "http://10.0.0.1/keepalive",
            120,
        ),
        (
            """
            <script>
                setInterval(function() {
                    fetch('/quickping');
                }, 10000);
            </script>
            """,
            "http://10.0.0.1/",
            "http://10.0.0.1/quickping",
            45,
        ),
    ],
)
def test_parse_js_keepalive_fixtures(html, base_url, expected_url, expected_interval):
    ki = parse_js_keepalive(html, base_url)
    assert ki is not None
    assert ki.url == expected_url
    assert ki.interval == expected_interval


def test_parse_js_keepalive_no_match():
    html = "<html><body><h1>Welcome</h1></body></html>"
    assert parse_js_keepalive(html, "http://10.0.0.1/") is None


def test_parse_keepalive_meta_refresh_preference():
    html = """
    <html>
        <head>
            <meta http-equiv="refresh" content="300;url=/meta-keepalive">
            <script>
                setInterval(function() { fetch('/js-keepalive'); }, 120000);
            </script>
        </head>
    </html>
    """
    ki = parse_keepalive(html, "http://10.0.0.1/")
    assert ki is not None
    assert ki.url == "http://10.0.0.1/meta-keepalive"
    assert ki.interval == 300


def test_parse_keepalive_fallback_to_js():
    html = """
    <html>
        <head>
            <script>
                setInterval(function() { fetch('/js-keepalive'); }, 120000);
            </script>
        </head>
    </html>
    """
    ki = parse_keepalive(html, "http://10.0.0.1/")
    assert ki is not None
    assert ki.url == "http://10.0.0.1/js-keepalive"
    assert ki.interval == 120

