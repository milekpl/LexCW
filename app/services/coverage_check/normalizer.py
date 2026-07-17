"""
Text normalization for coverage checking.

Handles apostrophe normalization (typographical → ASCII),
whitespace collapsing, and case folding.
"""
from __future__ import annotations

# Typographical apostrophe variants → ASCII apostrophe
_APOSTROPHE_MAP = {
    "\u2019": "'",  # RIGHT SINGLE QUOTATION MARK
    "\u2018": "'",  # LEFT SINGLE QUOTATION MARK
    "\uff07": "'",  # FULLWIDTH APOSTROPHE
    "\u02bc": "'",  # MODIFIER LETTER APOSTROPHE
}


def normalize(text: str | None) -> str:
    """Normalize text for case-insensitive comparison.

    - Lowercase
    - Normalize typographical apostrophes to ASCII
    - Collapse whitespace
    - Strip leading/trailing whitespace
    """
    if not text:
        return ""
    result = text
    for old, new in _APOSTROPHE_MAP.items():
        result = result.replace(old, new)
    result = " ".join(result.split())
    return result.lower().strip()


def normalize_strict(text: str | None) -> str:
    """Normalize text preserving case (for proper noun matching).

    - Normalize typographical apostrophes to ASCII
    - Collapse whitespace
    - Strip leading/trailing whitespace
    - Preserve original case
    """
    if not text:
        return ""
    result = text
    for old, new in _APOSTROPHE_MAP.items():
        result = result.replace(old, new)
    return " ".join(result.split()).strip()
