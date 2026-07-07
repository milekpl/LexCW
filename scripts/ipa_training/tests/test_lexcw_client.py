"""Unit tests for the LexCW client (no network required)."""

from __future__ import annotations

import json
from pathlib import Path

from lexcw_client import LexCWClient


def _sample_entry() -> dict:
    return {
        "id": "e1",
        "lexical_unit": {"en": "cat", "pl": "kot"},
        "pronunciations": {"seh-fonipa": "kɔt"},
        "grammatical_info": "Noun",
    }


def test_extract_pair_from_entry():
    pair = LexCWClient.extract_pair(_sample_entry())
    assert pair is not None
    assert pair.headword == "cat"
    assert pair.ipa == "kɔt"
    assert pair.pos == "Noun"
    assert pair.entry_id == "e1"


def test_extract_pair_missing_ipa_returns_none():
    entry = {"lexical_unit": {"en": "cat"}, "pronunciations": {}}
    assert LexCWClient.extract_pair(entry) is None


def test_extract_pair_falls_back_to_headword_key():
    entry = {"headword": "dog", "pronunciations": {"seh-fonipa": "dɔg"}}
    pair = LexCWClient.extract_pair(entry)
    assert pair is not None
    assert pair.headword == "dog"


def test_extract_pair_custom_ipa_writing_system():
    entry = {"lexical_unit": {"en": "bird"}, "pronunciations": {"x-ipa": "bɜːd"}}
    pair = LexCWClient.extract_pair(entry, ipa_writing_system="x-ipa")
    assert pair is not None
    assert pair.ipa == "bɜːd"


def test_load_pairs_from_extracted_data_shape(tmp_path: Path):
    payload = {
        "data": [
            {"lexeme": "kot", "phoneme": "kɔt", "pos": "n"},
            {"lexeme": "pies", "phoneme": "pʲɛs", "pos": "n"},
            {"lexeme": "dom", "ipa": "dɔm"},
        ]
    }
    path = tmp_path / "pairs.json"
    path.write_text(json.dumps(payload), encoding="utf-8")

    pairs = LexCWClient.load_pairs_from_file(str(path))
    assert len(pairs) == 3
    assert pairs[0].headword == "kot"
    assert pairs[0].ipa == "kɔt"
    assert pairs[0].pos == "n"
    assert pairs[2].ipa == "dɔm"


def test_load_pairs_from_plain_list(tmp_path: Path):
    payload = [
        {"headword": "cat", "ipa": "kæt"},
        {"lexeme": "dog", "phoneme": "dɔg"},
    ]
    path = tmp_path / "pairs.json"
    path.write_text(json.dumps(payload), encoding="utf-8")

    pairs = LexCWClient.load_pairs_from_file(str(path))
    assert [p.headword for p in pairs] == ["cat", "dog"]


class _FakeClient(LexCWClient):
    """LexCWClient with canned paginated responses (no HTTP)."""

    def __init__(self, pages):
        super().__init__(base_url="http://test", project_id=1)
        self._pages = pages
        self._calls = 0

    def _get_json(self, url, params):
        page = params.get("page", 1)
        self._calls += 1
        return self._pages[page - 1]


def test_fetch_pairs_paginated():
    pages = [
        {
            "entries": [
                {"lexical_unit": {"en": "cat"}, "pronunciations": {"seh-fonipa": "kæt"}}
            ],
            "pages": 2,
        },
        {
            "entries": [
                {"lexical_unit": {"en": "dog"}, "pronunciations": {"seh-fonipa": "dɔg"}}
            ],
            "pages": 2,
        },
    ]
    client = _FakeClient(pages)
    pairs = client.fetch_pairs()
    assert len(pairs) == 2
    assert [p.headword for p in pairs] == ["cat", "dog"]
