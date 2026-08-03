import keyring

APP_NAME = "camp-fi"

def set_password(profile: str, username: str, password: str) -> None:
    """Securely store password in OS keyring."""
    keyring.set_password(f"{APP_NAME}-{profile}", username, password)

def get_password(profile: str, username: str) -> str | None:
    """Retrieve password from OS keyring."""
    return keyring.get_password(f"{APP_NAME}-{profile}", username)

def delete_password(profile: str, username: str) -> None:
    """Delete password from OS keyring."""
    try:
        keyring.delete_password(f"{APP_NAME}-{profile}", username)
    except keyring.errors.PasswordDeleteError:
        pass
