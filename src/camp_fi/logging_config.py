import logging
import re

class RedactingFormatter(logging.Formatter):
    def __init__(self, fmt=None):
        super().__init__(fmt)
        # Redact common sensitive patterns
        self.patterns = [
            (re.compile(r"((?:password|passwd|pwd|token|magic|cookie|authorization|session|secret|bearer)[=:]\s*)['\"]?[^\s'\"&]+['\"]?", re.IGNORECASE), r"\1***"),
            (re.compile(r"([?&](?:password|passwd|pwd|token|magic|cookie|authorization|session|secret)=)[^&\s]+", re.IGNORECASE), r"\1***"),
            (re.compile(r"(Bearer\s+)[a-zA-Z0-9_\-\.]+", re.IGNORECASE), r"\1***"),
        ]

    def format(self, record):
        msg = super().format(record)
        for pattern, replacement in self.patterns:
            msg = pattern.sub(replacement, msg)
        return msg

def setup_logging(level=logging.INFO):
    logger = logging.getLogger("camp-fi")
    logger.setLevel(level)
    
    if not logger.handlers:
        ch = logging.StreamHandler()
        ch.setLevel(level)
        formatter = RedactingFormatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
        ch.setFormatter(formatter)
        logger.addHandler(ch)
    
    return logger
