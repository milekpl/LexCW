from __future__ import annotations

import pytest


def test_settings_page_handles_missing_dict_service(client, app, monkeypatch):
    """Simulate injector failing to provide DictionaryService and ensure /settings renders."""
    # Monkeypatch injector.get to raise for DictionaryService
    inj = app.injector

    orig_get = inj.get

    def bad_get(interface, *args, **kwargs):
        from app.services.dictionary_service import DictionaryService
        if interface is DictionaryService:
            raise RuntimeError('Injector missing DictionaryService')
        return orig_get(interface, *args, **kwargs)

    monkeypatch.setattr(inj, 'get', bad_get)

    resp = client.get('/settings/')
    assert resp.status_code == 200
    assert b'Project Settings' in resp.data
