import httpx
from camp_fi.portals.iiitk import IIITKAdapter
from camp_fi.portals.fortinet import FortinetAdapter
from camp_fi.portals.generic_form import GenericFormAdapter

def test_generic_form_adapter_match():
    adapter = GenericFormAdapter()
    html = """
    <html><body>
    <form action="/login" method="POST">
        <input type="text" name="user">
        <input type="password" name="pass">
    </form>
    </body></html>
    """
    assert adapter.matches(html, "http://192.168.1.1/index.html") is True

    no_form = "<html><body>No form here</body></html>"
    assert adapter.matches(no_form, "http://192.168.1.1/index.html") is False

def test_iiitk_adapter_match():
    adapter = IIITKAdapter()
    assert adapter.matches("<html></html>", "https://auth.iiitkottayam.ac.in/login") is True
    assert adapter.matches("<html>auth.iiitkottayam.ac.in</html>", "http://10.0.0.1/") is True
    assert adapter.matches("<html></html>", "http://google.com/") is False

def test_fortinet_adapter_match():
    adapter = FortinetAdapter()
    html = '<html><input name="magic" value="12345">fgtauth</html>'
    assert adapter.matches(html, "http://1.1.1.1:1000/login") is True
    assert adapter.matches("<html>no magic</html>", "http://google.com/") is False
