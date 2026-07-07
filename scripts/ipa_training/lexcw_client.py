# encoding: UTF-8
"""
LexCW client - fetch grapheme/IPA training pairs from the LexCW API.

This replaces the SIL FieldWorks CSV-export extraction step in the original
Wielki G2P pipeline. Instead of reading a FLEx project, it pulls entries
directly from a running LexCW instance via ``GET /api/entries/`` and extracts
``(headword, IPA)`` pairs (headword from ``lexical_unit``, IPA from
``pronunciations[<ipa_writing_system>]``).

The client uses only the Python standard library (``urllib``) so it can run in
a lightweight training environment without extra HTTP dependencies.

Example:
    client = LexCWClient(base_url="http://localhost:5000",
                          api_key="sw_xxxx", project_id=1)
    pairs = client.fetch_pairs()
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

try:  # Prefer requests when available (friendlier API), fall back to urllib.
    import requests

    _HAS_REQUESTS = True
except ImportError:  # pragma: no cover - exercised only without requests
    import urllib.request
    import urllib.error

    _HAS_REQUESTS = False


DEFAULT_IPA_WRITING_SYSTEM = "seh-fonipa"


def _expand_parenthetical(ipa: str) -> List[str]:
    """Return all expansions of ``ipa`` with parenthetical groups removed.

    Each ``(...)`` group is treated as optional, so a string with one group
    yields two variants (with and without the inner text). Groups may nest and
    repeat. Unbalanced parentheses are kept literally.
    """
    idx = ipa.find("(")
    if idx == -1:
        return [ipa]

    depth = 0
    close = -1
    for i in range(idx, len(ipa)):
        if ipa[i] == "(":
            depth += 1
        elif ipa[i] == ")":
            depth -= 1
            if depth == 0:
                close = i
                break

    if close == -1:
        return [ipa]

    before = ipa[:idx]
    inside = ipa[idx + 1 : close]
    after = ipa[close + 1 :]

    variants: List[str] = []
    for expanded in (before + inside + after, before + after):
        variants.extend(_expand_parenthetical(expanded))
    return variants


def decompress_ipa(ipa: str) -> str:
    """Return a single canonical decompressed form (shortest variant).

    Parenthetical IPA notation (e.g. ``ˈskɒtɪˌsɪz(ə)m``) is expanded into its
    optional-free form so optional segments never cause false mismatches during
    G2P training or anomaly detection.
    """
    if not ipa:
        return ipa
    variants = sorted({v for v in _expand_parenthetical(ipa) if v != ""})
    if not variants:
        return ipa
    return min(variants, key=lambda s: (len(s), s))


@dataclass
class LexCWPair:
    """A single grapheme/IPA training pair extracted from LexCW."""

    headword: str
    ipa: str
    pos: Optional[str] = None
    entry_id: Optional[str] = None

    def as_tuple(self) -> Tuple[str, str, Optional[str]]:
        """Return ``(headword, ipa, pos)`` for training pipelines."""
        return (self.headword, self.ipa, self.pos)


class LexCWClient:
    """Client for extracting G2P training pairs from a LexCW instance."""

    def __init__(
        self,
        base_url: str,
        api_key: Optional[str] = None,
        project_id: Optional[int] = None,
        ipa_writing_system: str = DEFAULT_IPA_WRITING_SYSTEM,
        timeout: float = 60.0,
        per_page: int = 200,
    ) -> None:
        """
        Initialize the client.

        Args:
            base_url: Root URL of the LexCW instance (e.g. ``http://localhost:5000``).
            api_key: Optional ``sw_...`` API key sent as a Bearer token.
            project_id: Project the entries belong to (sent as a query parameter).
            ipa_writing_system: Writing-system code holding IPA pronunciations.
            timeout: HTTP timeout in seconds.
            per_page: Page size for entry pagination.
        """
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.project_id = project_id
        self.ipa_writing_system = ipa_writing_system
        self.timeout = timeout
        self.per_page = per_page

    def _headers(self) -> Dict[str, str]:
        headers = {"Accept": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers

    def _get_json(self, url: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Perform a GET request and return parsed JSON (stdlib or requests)."""
        if _HAS_REQUESTS:
            resp = requests.get(
                url, headers=self._headers(), params=params, timeout=self.timeout
            )
            resp.raise_for_status()
            return resp.json()

        # stdlib fallback
        from urllib.parse import urlencode

        full = f"{url}?{urlencode(params)}"
        req = urllib.request.Request(full, headers=self._headers(), method="GET")
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as fh:
                body = fh.read().decode("utf-8")
        except urllib.error.HTTPError as exc:  # pragma: no cover - network path
            raise RuntimeError(f"LexCW request failed: {exc.code} {exc.reason}") from exc
        return json.loads(body)

    def iter_entries(self) -> Any:
        """
        Iterate over all entries across paginated API responses.

        Yields:
            Raw entry dictionaries as returned by the API.
        """
        page = 1
        while True:
            params: Dict[str, Any] = {
                "page": page,
                "per_page": self.per_page,
            }
            if self.project_id is not None:
                params["project_id"] = self.project_id

            data = self._get_json(f"{self.base_url}/api/entries/", params)
            entries = data.get("entries") or []
            if not entries:
                break

            for entry in entries:
                yield entry

            total_pages = data.get("pages") or data.get("total_pages")
            if total_pages and page >= int(total_pages):
                break
            page += 1

    def fetch_pairs(self) -> List[LexCWPair]:
        """
        Fetch and extract ``(headword, IPA)`` pairs from the LexCW API.

        Returns:
            List of :class:`LexCWPair` with both a headword and an IPA value.
        """
        pairs: List[LexCWPair] = []
        for entry in self.iter_entries():
            pair = self.extract_pair(entry, ipa_writing_system=self.ipa_writing_system)
            if pair is not None:
                pairs.append(pair)
        return pairs

    @staticmethod
    def extract_pair(
        entry: Dict[str, Any],
        ipa_writing_system: str = DEFAULT_IPA_WRITING_SYSTEM,
    ) -> Optional[LexCWPair]:
        """
        Extract a single ``(headword, IPA)`` pair from a LexCW entry dict.

        Args:
            entry: Entry dictionary as returned by ``GET /api/entries/``.
            ipa_writing_system: Writing-system code holding IPA pronunciations.

        Returns:
            A :class:`LexCWPair` or ``None`` when no headword/IPA is present.
        """
        headword = LexCWClient._extract_headword(entry)
        ipa = LexCWClient._extract_ipa(entry, ipa_writing_system)
        if not headword or not ipa:
            return None

        pos = entry.get("grammatical_info") or None
        if isinstance(pos, dict):
            pos = pos.get("value") or next(iter(pos.values()), None)
        entry_id = entry.get("id") or entry.get("entry_id")

        return LexCWPair(
            headword=headword, ipa=ipa, pos=pos, entry_id=str(entry_id) if entry_id else None
        )

    @staticmethod
    def _extract_headword(entry: Dict[str, Any]) -> str:
        lexical_unit = entry.get("lexical_unit") or {}
        if isinstance(lexical_unit, dict) and lexical_unit:
            if "en" in lexical_unit:
                return str(lexical_unit["en"])
            return str(next(iter(lexical_unit.values())))
        headword = entry.get("headword")
        return str(headword) if headword else ""

    @staticmethod
    def _extract_ipa(entry: Dict[str, Any], ipa_writing_system: str) -> str:
        pronunciations = entry.get("pronunciations") or {}
        if isinstance(pronunciations, dict):
            value = pronunciations.get(ipa_writing_system) or pronunciations.get("ipa")
            if value:
                return decompress_ipa(str(value))
        # Some entries store pronunciation under a different key shape.
        pronunciation = entry.get("pronunciation")
        if isinstance(pronunciation, dict):
            value = pronunciation.get(ipa_writing_system) or pronunciation.get("ipa")
            if value:
                return decompress_ipa(str(value))
        return ""

    @staticmethod
    def load_pairs_from_file(path: str) -> List[LexCWPair]:
        """
        Load pairs from a JSON file (offline mode, no API call).

        Supports both the g2p ``extracted_data.json`` shape (``{"data": [...]}``)
        and a plain list of objects with ``lexeme``/``headword`` and
        ``phoneme``/``ipa`` fields.

        Args:
            path: Path to the JSON file.

        Returns:
            List of :class:`LexCWPair`.
        """
        with open(path, "r", encoding="utf-8") as fh:
            data = json.load(fh)

        raw_items = data.get("data", data) if isinstance(data, dict) else data
        pairs: List[LexCWPair] = []
        for item in raw_items:
            lexical_unit = item.get("lexical_unit")
            if isinstance(lexical_unit, dict):
                headword = (
                    item.get("headword") or item.get("lexeme") or lexical_unit.get("en")
                )
            else:
                headword = item.get("headword") or item.get("lexeme") or lexical_unit
            ipa = item.get("ipa") or item.get("phoneme")
            if not headword or not ipa:
                continue
            pairs.append(
                LexCWPair(
                    headword=str(headword),
                    ipa=decompress_ipa(str(ipa)),
                    pos=item.get("pos"),
                    entry_id=str(item["id"]) if item.get("id") else None,
                )
            )
        return pairs


def pairs_to_training_data(pairs: List[LexCWPair]) -> List[Tuple[str, str]]:
    """
    Convert extracted pairs to the ``(grapheme, phoneme)`` tuples the G2P
    trainer expects.

    Args:
        pairs: Extracted LexCW pairs.

    Returns:
        List of ``(headword, ipa)`` tuples.
    """
    return [(p.headword, p.ipa) for p in pairs]
