from camp_fi.systemd import render_service_unit

def test_render_service_unit():
    unit = render_service_unit("/usr/bin/python3 -m camp_fi daemon --foreground")
    assert "ExecStart=/usr/bin/python3 -m camp_fi daemon --foreground" in unit
    assert "Wants=network-online.target" in unit
    assert "After=network-online.target" in unit
    assert "Restart=on-failure" in unit
    assert "RestartSec=15" in unit
