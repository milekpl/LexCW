#!/usr/bin/env python3
"""
Test morph-type respect for existing LIFT data
"""

from __future__ import annotations
import pytest
from app.models.entry import Entry
from app.services.dictionary_service import DictionaryService

@pytest.mark.integration
class TestMorphTypeInheritance:
    """Test that morph-type respects existing LIFT data and doesn't auto-override"""

    def test_existing_morph_type_not_overridden(self, dict_service_with_db: DictionaryService):
        """Entries with existing morph-type in LIFT aren't overridden"""
        # Ensure clean state
        try:
            existing = dict_service_with_db.get_entry('test-morph-123')
            if existing:
                dict_service_with_db.delete_entry('test-morph-123')
        except Exception:
            pass

        entry_data = {
            'id_': 'test-morph-123',
            'lexical_unit': {'en': 'Protestant'},
            'morph_type': 'stem',
            'senses': [{'id': 'sense1', 'glosses': {'en': 'test definition'}}]
        }

        entry = Entry.from_dict(entry_data)
        assert entry.morph_type == 'stem'

        created_id = dict_service_with_db.create_entry(entry)
        assert created_id == 'test-morph-123'

        retrieved = dict_service_with_db.get_entry(created_id)
        assert retrieved.morph_type == 'stem'

        # Modify lexical unit and ensure morph_type preserved on update
        entry_data_modified = {
            'id_': 'test-morph-123',
            'lexical_unit': {'en': 'pre-'},
            'morph_type': 'stem',
            'senses': [{'id': 'sense1', 'glosses': {'en': 'test definition'}}]
        }
        modified_entry = Entry.from_dict(entry_data_modified)
        assert modified_entry.morph_type == 'stem'

        dict_service_with_db.update_entry(modified_entry)
        final_entry = dict_service_with_db.get_entry(created_id)
        assert final_entry.morph_type == 'stem'

    def test_empty_morph_type_gets_auto_classified(self, dict_service_with_db: DictionaryService):
        """Entries with no morph-type get auto-classified"""
        try:
            existing = dict_service_with_db.get_entry('test-morph-456')
            if existing:
                dict_service_with_db.delete_entry('test-morph-456')
        except Exception:
            pass

        entry_data = {
            'id_': 'test-morph-456',
            'lexical_unit': {'en': 'test-suffix'},
            'morph_type': '',
            'senses': [{'id': 'sense1', 'glosses': {'en': 'test definition'}}]
        }

        entry = Entry.from_dict(entry_data)
        assert 'suffix' in entry.morph_type.lower()

        dict_service_with_db.create_entry(entry)
        retrieved = dict_service_with_db.get_entry(entry.id)
        assert 'suffix' in retrieved.morph_type.lower()

    def test_morph_type_patterns(self):
        """Test various morph-type classification patterns"""
        test_cases = [
            ({'en': 'word'}, None, 'stem'),
            ({'en': 'multi word'}, None, 'phrase'),
            ({'en': 'pre-'}, None, 'prefix'),
            ({'en': '-suf'}, None, 'suffix'),
            ({'en': '-in-'}, None, 'infix'),
            ({'en': 'word'}, 'phrase', 'phrase'),
            ({'en': ''}, None, 'stem'),
            ({'en': 'pre-'}, 'stem', 'stem'),
        ]

        for lexical_unit, explicit_morph_type, expected in test_cases:
            data = {'lexical_unit': lexical_unit}
            if explicit_morph_type:
                data['morph_type'] = explicit_morph_type

            entry = Entry.from_dict(data)
            assert entry.morph_type == expected

    def test_lift_data_preservation(self):
        """Test that LIFT data is preserved and not overridden"""
        from app.parsers.lift_parser import LIFTParser

        xml_with_morph_type = '''<entry id="test-entry-preservation">
            <lexical-unit>
                <form lang="en">
                    <text>Protestant</text>
                </form>
            </lexical-unit>
            <trait name="morph-type" value="stem"/>
            <sense id="sense1">
                <gloss lang="en">
                    <text>test definition</text>
                </gloss>
            </sense>
        </entry>'''

        parser = LIFTParser()
        entries = parser.parse_string(xml_with_morph_type)
        assert len(entries) == 1
        entry = entries[0]
        assert entry.morph_type == 'stem'
        assert entry.lexical_unit.get('en') == 'Protestant'

    def test_flask_app_morph_type_handling(self, client, dict_service_with_db: DictionaryService):
        """Test Flask app preserves morph-type from LIFT using `client` fixture"""
        # Create entry in the DB
        entry = Entry(
            id_='test-entry-1',
            lexical_unit={'en': 'Protestant'},
            morph_type='stem',
            senses=[{'id': 'sense1', 'glosses': {'en': 'def'}}]
        )
        dict_service_with_db.create_entry(entry)

        # Request the edit form
        response = client.get('/entries/test-entry-1/edit')
        assert response.status_code == 200
        html = response.data.decode('utf-8')

        # Check for lexical unit and morph-type present in form
        assert 'value="Protestant"' in html
        assert 'value="stem"' in html or 'data-selected="stem"' in html