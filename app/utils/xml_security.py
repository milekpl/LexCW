"""
XML security helpers — safe parsing that guards against XXE and bomb attacks.

Two layers of defence:

1. :func:`reject_xxe` — fast regex-based heuristic (defence-in-depth, kept for
   backward compatibility with existing callers).

2. :func:`safe_et_fromstring` / :func:`safe_et_parse` — use
   :mod:`defusedxml.ElementTree` (the stdlib-adjacent security wrapper) which
   correctly blocks billion-laughs, quadratic blowup, external entity
   resolution, DTD retrieval, and encoding-trick variants that regex cannot
   detect.
"""

import re
from pathlib import Path
from typing import Any, Optional, Protocol

import defusedxml.ElementTree as DefusedET


# Keep the regex-based fast path for existing callers (defence-in-depth).
_DOCTYPE_RE = re.compile(r"<!\s*doctype", flags=re.IGNORECASE)
_ENTITY_RE = re.compile(r"<!\s*entity", flags=re.IGNORECASE)


class _ETModule(Protocol):
    """Protocol for the parts of ElementTree we use.

    This lets unit tests monkeypatch/replace the module while we still
    enforce security checks via defusedxml by default.
    """

    def fromstring(self, text: str) -> Any: ...
    def parse(self, file: str) -> Any: ...


# ---------------------------------------------------------------------------
# Layer 1 — fast heuristic (backward-compatible)
# ---------------------------------------------------------------------------


def reject_xxe(xml: Optional[str]) -> None:
    """Fail closed against obvious XXE/entity declarations (fast path).

    This is a **heuristic** — it catches simple DOCTYPE and ENTITY
    declarations via regex.  The real security comes from using
    :func:`safe_et_fromstring` / :func:`safe_et_parse` which delegate
    to :mod:`defusedxml` and handle encoding tricks, parameter
    entities, and other bypasses.

    Args:
        xml: XML string to inspect.

    Raises:
        ValueError: If the XML contains a DOCTYPE or ENTITY declaration.
    """
    if not xml:
        return
    if _DOCTYPE_RE.search(xml) or _ENTITY_RE.search(xml):
        raise ValueError(
            "XML_SECURITY_ERROR: DOCTYPE/ENTITY declarations are not allowed"
        )


# ---------------------------------------------------------------------------
# Layer 2 — defusedxml (correct security)
# ---------------------------------------------------------------------------


def _get_parser() -> _ETModule:
    """Return the :mod:`defusedxml.ElementTree` module.

    Exposed as a function so tests can override it.
    """
    return DefusedET  # type: ignore[return-value]


def safe_et_fromstring(
    et_module: Optional[_ETModule] = None,
    xml: str = "",
) -> Any:
    """Parse XML from a string, safely.

    Uses :mod:`defusedxml.ElementTree` by default, which blocks:
    - Billion laughs (entity expansion)
    - Quadratic blowup
    - External entity (XXE) resolution
    - DTD retrieval

    Args:
        et_module: ElementTree module (defaults to defusedxml).
        xml: XML string to parse.

    Returns:
        Parsed XML element tree.

    Raises:
        Various XML parse errors (including :exc:`ValueError` for
        dangerous constructs caught by defusedxml).
    """
    if et_module is None:
        et_module = _get_parser()
    return et_module.fromstring(xml)


def safe_et_parse(
    et_module: Optional[_ETModule] = None,
    file_path: str = "",
) -> Any:
    """Parse XML from a file path, safely.

    Uses :mod:`defusedxml.ElementTree` which protects against XXE and
    entity-expansion attacks without relying on regex heuristics.

    Args:
        et_module: ElementTree module (defaults to defusedxml).
        file_path: Path to the XML file.

    Returns:
        Parsed XML element tree.
    """
    if et_module is None:
        et_module = _get_parser()
    return et_module.parse(file_path)
