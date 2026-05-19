import re

# Applied in order — TFN first so 9-digit patterns are caught before 6-digit BSB sub-matches
_TFN_RE = re.compile(r"\b\d{3}-\d{3}-\d{3}\b")
_BSB_RE = re.compile(r"\b\d{6}\b")
_ACCT_RE = re.compile(r"\b\d{8,16}\b")


def _scrub(text: str) -> str:
    text = _TFN_RE.sub("[TFN]", text)
    text = _BSB_RE.sub("[BSB]", text)
    text = _ACCT_RE.sub("[ACCT]", text)
    return text


def sanitize_for_ai(
    text: str | None, fields: dict | None
) -> tuple[str | None, dict | None]:
    """Remove TFN, BSB, and account numbers from text and string values in fields."""
    clean_text = _scrub(text) if text else text
    clean_fields: dict | None = None
    if fields is not None:
        clean_fields = {
            k: _scrub(v) if isinstance(v, str) else v
            for k, v in fields.items()
        }
    return clean_text, clean_fields
