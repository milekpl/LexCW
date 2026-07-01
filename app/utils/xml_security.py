import re
from pathlib import Path
from typing import Any, Protocol


class _ETModule(Protocol):
    """Small protocol for the parts of ElementTree we use.

    This lets unit tests monkeypatch/replace the module (they often patch
    `app.parsers.*.ET`) while we still enforce security checks.
    """

    def fromstring(self, text: str) -> Any: ...
    def parse(self, file: str) -> Any: ...


_DOCTYPE_RE = re.compile(r"<!\s*doctype", flags=re.IGNORECASE)
_ENTITY_RE = re.compile(r"<!\s*entity", flags=re.IGNORECASE)


def reject_xxe(xml: str) -> None:
    """Fail closed against common XXE vectors.

    We reject XML that contains a DOCTYPE or ENTITY declaration.
    This blocks both external entity expansion and internal entity
    expansion (often used for exponential blowups / data disclosure).
    """

    if xml is None:
        return
    if _DOCTYPE_RE.search(xml) or _ENTITY_RE.search(xml):
        # Keep the message generic; callers map it to a consistent error.
        raise ValueError("XML_SECURITY_ERROR: DOCTYPE/ENTITY declarations are not allowed")


def safe_et_fromstring(et_module: _ETModule, xml: str) -> Any:
    reject_xxe(xml)
    return et_module.fromstring(xml)


def safe_et_parse(et_module: _ETModule, file_path: str) -> Any:
    """Parse XML from a file path with a best-effort security scan."""

    try:
        content = Path(file_path).read_text(encoding="utf-8", errors="replace")
        reject_xxe(content)
    except OSError:
        # If we can't read the file (or tests use fake paths), defer to the
        # underlying XML parser to raise a meaningful error.
        pass
    return et_module.parse(file_path)
