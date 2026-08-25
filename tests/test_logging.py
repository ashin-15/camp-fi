import logging
from camp_fi.logging_config import RedactingFormatter

def test_redacting_formatter():
    formatter = RedactingFormatter("%(message)s")
    record = logging.LogRecord("test", logging.INFO, "", 0, "Logging password=secret123 and token=abc", (), None)
    formatted = formatter.format(record)
    assert "password=***" in formatted
    assert "token=***" in formatted
    assert "secret123" not in formatted

def test_redacting_url_query_params():
    formatter = RedactingFormatter("%(message)s")
    record = logging.LogRecord("test", logging.INFO, "", 0, "GET /login?magic=xyz123&password=mysecret", (), None)
    formatted = formatter.format(record)
    assert "magic=***" in formatted
    assert "password=***" in formatted
    assert "xyz123" not in formatted
    assert "mysecret" not in formatted

def test_setup_logging():
    from camp_fi.logging_config import setup_logging
    logger = setup_logging(logging.DEBUG)
    assert logger.name == "camp-fi"
    assert logger.level == logging.DEBUG
    assert len(logger.handlers) >= 1

def test_credentials_logging(caplog):
    import keyring
    from unittest.mock import patch
    from camp_fi.credentials import set_password, get_password, delete_password
    from camp_fi.logging_config import setup_logging

    setup_logging(logging.DEBUG)
    with caplog.at_level(logging.DEBUG, logger="camp-fi"), \
         patch("keyring.set_password"), \
         patch("keyring.get_password", return_value="secretpass"), \
         patch("keyring.delete_password"):
        set_password("testprof", "user1", "secretpass")
        assert "Storing credentials in keyring for profile 'testprof' (user: 'user1')." in caplog.text

        pw = get_password("testprof", "user1")
        assert pw == "secretpass"
        assert "Retrieving credentials from keyring for profile 'testprof' (user: 'user1')." in caplog.text

        delete_password("testprof", "user1")
        assert "Deleting credentials from keyring for profile 'testprof' (user: 'user1')." in caplog.text

def test_systemd_service_logging(caplog):
    from unittest.mock import patch
    from camp_fi.systemd import start_service, stop_service, restart_service, install_service, uninstall_service
    from camp_fi.logging_config import setup_logging

    setup_logging(logging.INFO)
    with caplog.at_level(logging.INFO, logger="camp-fi"), \
         patch("camp_fi.systemd._run_systemctl"), \
         patch("camp_fi.systemd.get_service_path") as mock_path:
        mock_file = mock_path.return_value
        mock_file.open.return_value.__enter__.return_value.write = lambda x: None
        mock_file.exists.return_value = True
        mock_file.unlink = lambda: None

        start_service()
        assert "Starting camp-fi systemd service..." in caplog.text
        assert "camp-fi systemd service started successfully." in caplog.text

        stop_service()
        assert "Stopping camp-fi systemd service..." in caplog.text
        assert "camp-fi systemd service stopped successfully." in caplog.text

        restart_service()
        assert "Restarting camp-fi systemd service..." in caplog.text
        assert "camp-fi systemd service restarted successfully." in caplog.text

        install_service()
        assert "Installing and starting camp-fi systemd service..." in caplog.text

        uninstall_service()
        assert "Uninstalling camp-fi systemd service..." in caplog.text

def test_captive_login_credential_passing_log(caplog):
    from unittest.mock import patch, MagicMock
    from camp_fi.net.captive import execute_login
    from camp_fi.net.probes import ProbeResult, ConnectivityStatus
    from camp_fi.logging_config import setup_logging

    setup_logging(logging.INFO)

    mock_resp = MagicMock()
    mock_resp.text = '<form action="/login" method="post"><input name="username"><input name="password" type="password"></form>'
    mock_resp.url = "http://portal.local/login.html"
    mock_resp.status_code = 200

    mock_post_resp = MagicMock()
    mock_post_resp.text = "<html>Logged in successfully</html>"
    mock_post_resp.url = "http://portal.local/success"
    mock_post_resp.status_code = 200

    mock_client = MagicMock()
    mock_client.__enter__.return_value = mock_client
    mock_client.get.return_value = mock_resp
    mock_client.post.return_value = mock_post_resp
    mock_client.send.return_value = mock_post_resp
    with caplog.at_level(logging.INFO, logger="camp-fi"), \
         patch("camp_fi.net.captive.build_http_client", return_value=mock_client), \
         patch("camp_fi.net.captive.check_connectivity", return_value=ProbeResult(ConnectivityStatus.INTERNET)):
        res = execute_login("http://portal.local", "student123", "secretpwd")
        assert res.succeeded
        assert "Passing credentials for user 'student123'" in caplog.text
        assert "secretpwd" not in caplog.text
def test_daemon_credential_passing_log(caplog, tmp_path, monkeypatch):
    import threading
    from unittest.mock import patch
    from camp_fi.config import AppConfig, ProfileConfig
    from camp_fi.daemon import run_daemon
    from camp_fi.models import LoginResult, LoginStatus
    from camp_fi.net.probes import ProbeResult, ConnectivityStatus
    from camp_fi.logging_config import setup_logging

    setup_logging(logging.INFO)
    monkeypatch.setattr("camp_fi.paths.get_config_dir", lambda: tmp_path)
    monkeypatch.setattr("camp_fi.paths.get_state_dir", lambda: tmp_path)

    dummy_config = AppConfig(profiles={
        "test": ProfileConfig(username="student99", ssids=["CampusNet"])
    })
    stop_event = threading.Event()

    def mock_login(*args, **kwargs):
        stop_event.set()
        return LoginResult(status=LoginStatus.SUCCESS, adapter_name="iiitk")

    with caplog.at_level(logging.INFO, logger="camp-fi"), \
         patch("camp_fi.daemon.load_config", return_value=dummy_config), \
         patch("camp_fi.daemon.get_current_ssid", return_value="CampusNet"), \
         patch("camp_fi.daemon.get_password", return_value="supersecretpassword"), \
         patch("camp_fi.daemon.check_connectivity", return_value=ProbeResult(ConnectivityStatus.CAPTIVE, redirect_url="http://login.campus.edu")), \
         patch("camp_fi.daemon.execute_login", side_effect=mock_login), \
         patch("camp_fi.daemon.record_event"), \
         patch.object(stop_event, "wait", side_effect=lambda timeout: stop_event.is_set()):
        run_daemon(stop_event=stop_event)

    assert "Captive portal detected at http://login.campus.edu for SSID 'CampusNet'. Passing credentials for profile 'test' (user: 'student99')..." in caplog.text
    assert "Successfully authenticated profile 'test' (user: 'student99') via adapter 'iiitk'." in caplog.text
    assert "supersecretpassword" not in caplog.text

def test_cli_global_logging_callback(tmp_path, monkeypatch):
    from typer.testing import CliRunner
    from camp_fi.cli import app
    import logging

    monkeypatch.setattr("camp_fi.paths.get_config_dir", lambda: tmp_path)
    monkeypatch.setattr("camp_fi.paths.get_state_dir", lambda: tmp_path)

    runner = CliRunner()
    res = runner.invoke(app, ["--verbose", "status"])
    assert res.exit_code == 0
    assert logging.getLogger("camp-fi").level == logging.DEBUG
