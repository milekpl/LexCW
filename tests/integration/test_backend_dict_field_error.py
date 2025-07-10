from __future__ import annotations
import logging
from app import create_app
from app.services.dictionary_service import DictionaryService
import pytest

@pytest.mark.integration
def test_update_entry_with_dict_field_logs_error(caplog):
    app = create_app()
    with app.app_context():
        dict_service = app.injector.get(DictionaryService)
        # Simulate a malformed entry with a dict where a string is expected
        entry = dict_service.get_entry("Protestantism_b97495fb-d52f-4755-94bf-a7a762339605")
        # Intentionally break a field
        entry.note = {"en": "This should be a string, not a dict"}
        with caplog.at_level(logging.ERROR):
            try:
                dict_service.update_entry(entry)
            except Exception as e:
                # The error should be logged and raised
                assert "write() argument must be str, not dict" in str(e)
                assert any("write() argument must be str, not dict" in m for m in caplog.messages)
