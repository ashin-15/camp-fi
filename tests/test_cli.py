from typer.testing import CliRunner

from camp_fi.cli import app

runner = CliRunner()

def test_cli_help():
    res = runner.invoke(app, ["--help"])
    assert res.exit_code == 0
    assert "Wi-Fi Captive Portal Auto-Login Daemon" in res.output

def test_cli_init():
    res = runner.invoke(app, ["init"])
    assert res.exit_code == 0
    assert "Initialization check complete" in res.output

def test_cli_profile_lifecycle(tmp_path, monkeypatch):
    monkeypatch.setattr("camp_fi.paths.get_config_dir", lambda: tmp_path)
    monkeypatch.setattr("camp_fi.paths.get_state_dir", lambda: tmp_path)

    # List default
    res = runner.invoke(app, ["profile", "list"])
    assert res.exit_code == 0

    # Add profile
    res = runner.invoke(app, ["profile", "add", "work"])
    assert res.exit_code == 0
    assert "Profile 'work' created." in res.output

    # Show profile
    res = runner.invoke(app, ["profile", "show", "work"])
    assert res.exit_code == 0
    assert "Profile: work" in res.output

def test_cli_status(tmp_path, monkeypatch):
    monkeypatch.setattr("camp_fi.paths.get_config_dir", lambda: tmp_path)
    monkeypatch.setattr("camp_fi.paths.get_state_dir", lambda: tmp_path)

    res = runner.invoke(app, ["status"])
    assert res.exit_code == 0
    assert "=== camp-fi status ===" in res.output

def test_cli_history(tmp_path, monkeypatch):
    from camp_fi.history import record_event
    from camp_fi.models import LoginResult, LoginStatus

    monkeypatch.setattr("camp_fi.paths.get_state_dir", lambda: tmp_path)
    record_event(tmp_path / "history.jsonl", "login_failed", "iiitk", LoginResult(LoginStatus.AUTH_FAILED, "test", message="bad pass"))

    res = runner.invoke(app, ["history", "--limit", "1"])

    assert res.exit_code == 0
    assert "login_failed profile=iiitk adapter=test status=AUTH_FAILED bad pass" in res.output
