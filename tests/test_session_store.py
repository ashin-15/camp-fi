import os
import json
import pytest
import httpx
from camp_fi.session_store import save_cookies, load_cookies, write_private_json

def test_write_private_json(tmp_path):
    target = tmp_path / "test.json"
    data = {"hello": "world"}
    write_private_json(target, data)

    assert target.exists()
    mode = oct(target.stat().st_mode & 0o777)
    assert mode == "0o600"

    with target.open() as f:
        loaded = json.load(f)
    assert loaded == data

def test_save_and_load_cookies(tmp_path):
    cookies_path = tmp_path / "cookies.json"
    client = httpx.Client()
    client.cookies.set("session", "abc123val", domain="example.com", path="/")

    save_cookies(client, cookies_path)
    assert cookies_path.exists()
    assert oct(cookies_path.stat().st_mode & 0o777) == "0o600"

    new_client = httpx.Client()
    load_cookies(new_client, cookies_path, "http://example.com")
    assert new_client.cookies.get("session", domain="example.com") == "abc123val"

def test_load_corrupt_cookies(tmp_path, caplog):
    cookies_path = tmp_path / "corrupt.json"
    cookies_path.write_text("{invalid json")

    client = httpx.Client()
    load_cookies(client, cookies_path, "http://example.com")
    assert not cookies_path.exists()
