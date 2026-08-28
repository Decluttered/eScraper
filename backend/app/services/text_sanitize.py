import re

_EMAIL_PATTERN = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
_PHONE_PATTERN = re.compile(r"(?:\+49[\s/-]?|0)1[5-7]\d(?:[\s/-]?\d){6,9}")
_REDACTED = "[REDACTED-CONTACT]"


def sanitize_import_text(text: str) -> str:
    text = _EMAIL_PATTERN.sub(_REDACTED, text)
    return _PHONE_PATTERN.sub(_REDACTED, text)
