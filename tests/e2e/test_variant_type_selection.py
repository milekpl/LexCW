"""
Integration test for variant type selection functionality.
Tests that the selected variant type is properly stored in the XML output as a trait.
"""

import pytest
import uuid
import tempfile
import os
import xml.etree.ElementTree as ET
from app.database.basex_connector import BaseXConnector
from app.services.dictionary_service import DictionaryService
from app.models.entry import Entry

# Connection parameters for test database
HOST = "localhost"
PORT = 1984
USERNAME = "admin"
PASSWORD = "admin"
TEST_DB_BASE = "test_variant_type"

# Minimal LIFT file to initialize the database structure
# Note: SIL Fieldworks doesn't actually use XML namespaces, so we omit them
MINIMAL_LIFT = '''<?xml version="1.0" encoding="UTF-8"?>
<lift version="0.13">
    <entries/>
</lift>
'''


@pytest.fixture(scope="function")
def dict_service():
    """Create a DictionaryService with a test database for each test."""
    # Generate a unique database name for this test run
    test_db = f"{TEST_DB_BASE}_{uuid.uuid4().hex[:8]}"

    # Create an admin connector (no database specified)
    admin_connector = BaseXConnector(HOST, PORT, USERNAME, PASSWORD)
    admin_connector.connect()

    # Clean up any existing test database
    try:
        if test_db in (admin_connector.execute_command("LIST") or ""):
            admin_connector.execute_command(f"DROP DB {test_db}")
    except Exception:
        pass

    # Create the test database
    admin_connector.execute_command(f"CREATE DB {test_db}")
    admin_connector.disconnect()

    # Now create a connector for the test database
    connector = BaseXConnector(HOST, PORT, USERNAME, PASSWORD, test_db)
    connector.connect()

    # Create the service
    service = DictionaryService(connector)

    # Initialize with minimal LIFT file using ADD command
    with tempfile.NamedTemporaryFile(mode='w', suffix='.xml', delete=False) as f:
        f.write(MINIMAL_LIFT)
        temp_file = f.name

    try:
        connector.execute_command(f"ADD {temp_file}")
    except Exception as e:
        print(f"Warning: Could not initialize database with minimal LIFT: {e}")
    finally:
        os.unlink(temp_file)

    yield service

    # Clean up
    try:
        connector.disconnect()
        admin_connector.connect()
        admin_connector.execute_command(f"DROP DB {test_db}")
        admin_connector.disconnect()
    except Exception:
        pass


@pytest.mark.integration
def test_variant_type_selection_stored_as_trait(dict_service):
    """Test that when user selects a variant type, it's stored as a trait in the XML."""

    # Generate unique ID for test isolation
    unique_id = f"test_entry_{uuid.uuid4().hex[:8]}"

    entry_data = {
        'id': unique_id,
        'lexical_unit': {'en': 'test word'},
        'grammatical_info': 'Noun',
        'variant_relations': [
            {
                'ref': f'variant_entry_{uuid.uuid4().hex[:8]}',
                'variant_type': 'spelling variant',
                'type': '_component-lexeme',
                'order': 0
            }
        ]
    }

    entry = Entry.from_dict(entry_data)

    # Create the entry in the database
    entry_id = dict_service.create_entry(entry)

    try:
        # Retrieve the entry to ensure it was properly saved
        retrieved_entry = dict_service.get_entry(entry_id)
        assert retrieved_entry.id == entry_id

        # Get the XML representation
        entry_xml_str = dict_service._prepare_entry_xml(retrieved_entry)

        # Parse the XML to verify the trait is present
        root = ET.fromstring(entry_xml_str)

        # Find all relations - use {}* to match any namespace
        relations = root.findall('.//{*}relation')
        variant_relations = [rel for rel in relations if rel.get('type') == '_component-lexeme']

        assert len(variant_relations) == 1, f"Expected 1 variant relation, found {len(variant_relations)}"

        variant_relation = variant_relations[0]

        # Find the trait with name="variant-type" - handle namespace
        traits = variant_relation.findall('.//{*}trait[@name="variant-type"]')
        assert len(traits) == 1, f"Expected 1 variant-type trait, found {len(traits)}"

        variant_trait = traits[0]
        assert variant_trait.get('value') == 'spelling variant', \
            f"Expected variant-type trait value 'spelling variant', got '{variant_trait.get('value')}'"

        print("Test passed: Variant type is properly stored as a trait in the XML")

    finally:
        # Clean up: delete the test entry
        try:
            dict_service.delete_entry(entry_id)
        except Exception:
            pass  # Entry might not exist if test failed early


@pytest.mark.integration
def test_multiple_variant_types(dict_service):
    """Test that multiple variant types are stored correctly."""

    # Generate unique IDs for test isolation
    unique_id = f"test_entry_multi_{uuid.uuid4().hex[:8]}"

    entry_data = {
        'id': unique_id,
        'lexical_unit': {'en': 'run'},
        'grammatical_info': 'Verb',
        'variant_relations': [
            {
                'ref': f'variant_entry_{uuid.uuid4().hex[:8]}',
                'variant_type': 'inflection',
                'type': '_component-lexeme',
                'order': 0
            },
            {
                'ref': f'variant_entry_{uuid.uuid4().hex[:8]}',
                'variant_type': 'dialectal variant',
                'type': '_component-lexeme',
                'order': 1
            }
        ]
    }

    entry = Entry.from_dict(entry_data)

    # Create the entry in the database
    entry_id = dict_service.create_entry(entry)

    try:
        # Retrieve and check XML
        retrieved_entry = dict_service.get_entry(entry_id)
        entry_xml_str = dict_service._prepare_entry_xml(retrieved_entry)
        root = ET.fromstring(entry_xml_str)

        # Find all variant relations - use {}* to match any namespace
        relations = root.findall('.//{*}relation')
        variant_relations = [rel for rel in relations if rel.get('type') == '_component-lexeme']

        assert len(variant_relations) == 2, f"Expected 2 variant relations, found {len(variant_relations)}"

        # Check that both have the correct variant-type traits
        variant_values = []
        for rel in variant_relations:
            traits = rel.findall('.//{*}trait[@name="variant-type"]')
            assert len(traits) == 1, "Each variant relation should have exactly one variant-type trait"
            variant_values.append(traits[0].get('value'))

        assert 'inflection' in variant_values
        assert 'dialectal variant' in variant_values

        print("Test passed: Multiple variant types are properly stored")

    finally:
        # Clean up
        try:
            dict_service.delete_entry(entry_id)
        except Exception:
            pass


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
