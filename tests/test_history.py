import json

from camp_fi.history import read_recent, record_event
from camp_fi.models import LoginResult, LoginStatus


def test_read_recent_returns_last_events_in_order(tmp_path):
    history_path = tmp_path / "history.jsonl"

    for idx in range(10):
        record_event(
            history_path,
            "login_failed",
            "iiitk",
            LoginResult(LoginStatus.AUTH_FAILED, "test", message=f"attempt {idx}"),
        )

    recent = read_recent(history_path, limit=5)

    assert [entry["message"] for entry in recent] == [f"attempt {idx}" for idx in range(5, 10)]
    assert {entry["event"] for entry in recent} == {"login_failed"}
    assert {entry["profile"] for entry in recent} == {"iiitk"}
    assert {entry["adapter"] for entry in recent} == {"test"}
    assert {entry["status"] for entry in recent} == {"AUTH_FAILED"}


def test_record_event_creates_private_history_file(tmp_path):
    history_path = tmp_path / "history.jsonl"

    record_event(history_path, "captive_detected", "iiitk")

    entries = read_recent(history_path)
    assert oct(history_path.stat().st_mode & 0o777) == "0o600"
    assert entries == [
        {
            "ts": entries[0]["ts"],
            "event": "captive_detected",
            "profile": "iiitk",
            "adapter": None,
            "status": None,
            "message": None,
        }
    ]


def test_record_event_rotates_before_appending(tmp_path, monkeypatch):
    history_path = tmp_path / "history.jsonl"
    monkeypatch.setattr("camp_fi.history.MAX_HISTORY_LINES", 6)
    monkeypatch.setattr("camp_fi.history.ROTATED_HISTORY_LINES", 3)

    history_path.write_text(
        "".join(json.dumps({"ts": idx, "message": f"old {idx}"}) + "\n" for idx in range(7))
    )

    record_event(
        history_path,
        "login_success",
        "iiitk",
        LoginResult(LoginStatus.SUCCESS, "fortinet", message="new"),
    )

    lines = history_path.read_text().splitlines()
    messages = [json.loads(line)["message"] for line in lines]
    assert messages == ["old 4", "old 5", "old 6", "new"]
    assert oct(history_path.stat().st_mode & 0o777) == "0o600"
