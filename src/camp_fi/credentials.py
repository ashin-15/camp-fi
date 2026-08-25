import logging
import keyring

APP_NAME = "camp-fi"
logger = logging.getLogger("camp-fi")

def set_password(profile: str, username: str, password: str) -> None:
    """Securely store password in OS keyring."""
    logger.info("Storing credentials in keyring for profile '%s' (user: '%s').", profile, username)
    keyring.set_password(f"{APP_NAME}-{profile}", username, password)

def get_password(profile: str, username: str) -> str | None:
    """Retrieve password from OS keyring."""
    logger.debug("Retrieving credentials from keyring for profile '%s' (user: '%s').", profile, username)
    return keyring.get_password(f"{APP_NAME}-{profile}", username)

def delete_password(profile: str, username: str) -> None:
    """Delete password from OS keyring."""
    logger.info("Deleting credentials from keyring for profile '%s' (user: '%s').", profile, username)
    try:
        keyring.delete_password(f"{APP_NAME}-{profile}", username)
    except keyring.errors.PasswordDeleteError:
        logger.warning("Password for profile '%s' (user: '%s') not found in keyring to delete.", profile, username)
