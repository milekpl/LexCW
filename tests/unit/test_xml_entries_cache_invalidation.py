from __future__ import annotations

import pytest
from flask import Flask

from app.api import xml_entries


class DummyService:
    def __init__(self) -> None:
        self.updated: list[tuple[str, str]] = []
        self.created: list[tuple[str, str]] = []

    def update_entry(self, entry_id: str, xml_string: str):
        self.updated.append((entry_id, xml_string))
        return {'id': entry_id, 'status': 'updated'}

    def create_entry(self, xml_string: str):
        # Fallback create path used when update raises EntryNotFoundError; not exercised here.
        self.created.append(('unknown', xml_string))
        return {'id': 'unknown', 'status': 'created'}


class DummyCache:
    def __init__(self) -> None:
        self.cleared_patterns: list[str] = []

    def is_available(self) -> bool:
        return True

    def clear_pattern(self, pattern: str) -> int:
        self.cleared_patterns.append(pattern)
        return 1


@pytest.fixture
def xml_app(monkeypatch: pytest.MonkeyPatch) -> tuple[Flask, DummyService, DummyCache]:
    """Create a Flask app with xml_entries blueprint and dummy services."""
    service = DummyService()
    cache = DummyCache()

    # Monkeypatch dependencies to avoid real BaseX/Redis access
    monkeypatch.setattr(xml_entries, 'get_xml_entry_service', lambda: service)

    # Patch CacheService inside the module and the underlying service module so the route uses DummyCache
    from app.services import cache_service
    monkeypatch.setattr(cache_service, 'CacheService', lambda: cache)
    monkeypatch.setattr(xml_entries, 'CacheService', lambda: cache, raising=False)

    app = Flask(__name__)
    app.config['TESTING'] = True
    app.register_blueprint(xml_entries.xml_entries_bp)

    return app, service, cache


def test_xml_update_clears_cache(xml_app: tuple[Flask, DummyService, DummyCache]) -> None:
    app, service, cache = xml_app
    client = app.test_client()

    xml_payload = (
        '<entry xmlns="http://fieldworks.sil.org/schemas/lift/0.13" id="cache_test">'
        '<lexical-unit><form lang="en"><text>word</text></form></lexical-unit>'
        '<sense id="s1"/></entry>'
    )

    response = client.put('/api/xml/entries/cache_test', data=xml_payload, headers={
        'Content-Type': 'application/xml'
    })

    assert response.status_code == 200
    assert ('cache_test', xml_payload) in service.updated
    assert 'entries:*' in cache.cleared_patterns
