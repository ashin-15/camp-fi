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
