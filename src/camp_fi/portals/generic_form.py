from bs4 import BeautifulSoup
from urllib.parse import urljoin

class FormInfo:
    def __init__(self, action: str, method: str, inputs: dict[str, str], user_field: str | None, pass_field: str | None):
        self.action = action
        self.method = method
        self.inputs = inputs
        self.user_field = user_field
        self.pass_field = pass_field

def parse_login_form(html: str, base_url: str) -> FormInfo | None:
    """Parse HTML and extract login form fields."""
    soup = BeautifulSoup(html, "html.parser")
    forms = soup.find_all("form")
    for form in forms:
        inputs = {}
        pass_field = None
        user_field = None
        
        for inp in form.find_all("input"):
            name = inp.get("name")
            if not name:
                continue
            
            val = inp.get("value", "")
            itype = inp.get("type", "text").lower()
            
            inputs[name] = val
            
            if itype == "password":
                pass_field = name
            elif itype in ("text", "email") or "user" in name.lower():
                if not user_field:
                    user_field = name
                    
        if pass_field:
            action = form.get("action", "")
            action_url = urljoin(base_url, action)
            method = form.get("method", "POST").upper()
            return FormInfo(action_url, method, inputs, user_field, pass_field)
            
    return None
