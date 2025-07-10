"""
Real integration tests without mocking.
These tests use actual database connections and real object interactions.
"""

import pytest
import tempfile
import os
from app.models.entry import Entry
from app.models.sense import Sense
from app.models.example import Example
from app.database.basex_connector import BaseXConnector
from app.services.dictionary_service import DictionaryService
from app.parsers.lift_parser import LIFTParser
from app.utils.exceptions import ValidationError, NotFoundError, DatabaseError


# Test configuration
TEST_HOST = "localhost"
TEST_PORT = 1984
TEST_USERNAME = "admin"
TEST_PASSWORD = "admin"
TEST_DB_PREFIX = "test_real_integration"



@pytest.mark.integration
class TestRealIntegration:
    """Real integration tests using actual database and services."""
    
    @pytest.fixture(scope="function")
    @pytest.mark.integration
    def test_db_name(self):
        """Generate a unique test database name for each test."""
        import uuid
        return f"{TEST_DB_PREFIX}_{str(uuid.uuid4()).replace('-', '_')}"
    
    @pytest.fixture(scope="function")
    def db_connector(self, test_db_name):
        """Create a real BaseX connector for testing."""
        # Create an admin connector (no database specified)
        admin_connector = BaseXConnector(TEST_HOST, TEST_PORT, TEST_USERNAME, TEST_PASSWORD)
        admin_connector.connect()
        
        # Clean up any existing test database
        try:
            if test_db_name in (admin_connector.execute_command("LIST") or ""):
                admin_connector.execute_command(f"DROP DB {test_db_name}")
        except Exception:
            pass
        
        # Create the test database
        admin_connector.execute_command(f"CREATE DB {test_db_name}")
        admin_connector.disconnect()
        
        # Now create a connector for the test database
        connector = BaseXConnector(TEST_HOST, TEST_PORT, TEST_USERNAME, TEST_PASSWORD, test_db_name)
        connector.connect()
        
        yield connector
        
        # Cleanup
        try:
            connector.disconnect()
            admin_connector.connect()
            admin_connector.execute_command(f"DROP DB {test_db_name}")
            admin_connector.disconnect()
        except Exception:
            pass
    
    @pytest.fixture(scope="function")
    def dict_service(self, db_connector):
        """Create a real DictionaryService with test database."""
        service = DictionaryService(db_connector)
        
        # Create minimal test LIFT data
        minimal_lift = '''<?xml version="1.0" encoding="UTF-8"?>
<lift version="0.15">
    <entry id="test_entry_init">
        <lexical-unit>
            <form lang="en"><text>test</text></form>
        </lexical-unit>
        <sense id="test_sense_init">
            <gloss lang="en"><text>initial test entry</text></gloss>
        </sense>
    </entry>
</lift>'''
        
        # Create temporary LIFT file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.lift', delete=False) as f:
            f.write(minimal_lift)
            temp_lift_path = f.name
        
        try:
            # Initialize database with test data
            service.initialize_database(temp_lift_path)
            yield service
        finally:
            # Cleanup temp file
            if os.path.exists(temp_lift_path):
                os.unlink(temp_lift_path)
    
    @pytest.mark.integration
    def test_real_entry_creation_and_retrieval(self, dict_service):
        """Test creating and retrieving entries with real database operations (multitext fields as dicts)."""
        entry = Entry(
            id_="real_test_entry",
            lexical_unit={"en": "integration", "pl": "integracja"},
            senses=[{
                "id": "real_sense_1",
                "definitions": {"en": {"text": "A comprehensive test of system components working together"}},
                "glosses": {"en": {"text": "The process of combining parts into a whole"}}
            }]
        )

        assert entry.validate()
        created_id = dict_service.create_entry(entry)
        assert created_id == "real_test_entry"

        retrieved_entry = dict_service.get_entry("real_test_entry")
        assert retrieved_entry is not None
        assert retrieved_entry.id == "real_test_entry"
        assert retrieved_entry.lexical_unit["en"] == "integration"
        assert len(retrieved_entry.senses) == 1
        assert retrieved_entry.senses[0].definitions["en"]["text"] == "A comprehensive test of system components working together"
        assert retrieved_entry.senses[0].glosses["en"]["text"] == "The process of combining parts into a whole"
    
    @pytest.mark.integration
    def test_real_search_functionality(self, dict_service):
        """Test search functionality with real database (multitext fields as dicts)."""
        entries = [
            Entry(
                id_="search_test_1",
                lexical_unit={"en": "apple", "pl": "jabłko"},
                senses=[{
                    "id": "apple_sense_1",
                    "definitions": {"en": {"text": "A red or green fruit that grows on trees"}},
                    "glosses": {"en": {"text": "A round fruit"}}
                }]
            ),
            Entry(
                id_="search_test_2",
                lexical_unit={"en": "application", "pl": "aplikacja"},
                senses=[{
                    "id": "app_sense_1",
                    "definitions": {"en": {"text": "Software designed for end users"}},
                    "glosses": {"en": {"text": "A computer program"}}
                }]
            ),
            Entry(
                id_="search_test_3",
                lexical_unit={"en": "appreciate", "pl": "doceniać"},
                senses=[{
                    "id": "appreciate_sense_1",
                    "definitions": {"en": {"text": "To understand the worth or importance of something"}},
                    "glosses": {"en": {"text": "To value or recognize"}}
                }]
            )
        ]
        
        # Add entries to database
        for entry in entries:
            dict_service.create_entry(entry)
        
        # Test basic search
        results, total = dict_service.search_entries("app")
        assert total >= 2  # Should find "apple" and "application"
        
        # Test exact search 
        results, total = dict_service.search_entries("apple")
        assert total >= 1
        found_apple = any(entry.lexical_unit.get("en") == "apple" for entry in results)
        assert found_apple
        
        # Test search in definitions
        results, total = dict_service.search_entries("computer program")
        assert total >= 1
        
        # Test pagination
        results_page1, total = dict_service.search_entries("", limit=2, offset=0)
        results_page2, _ = dict_service.search_entries("", limit=2, offset=2)
        
        # Should have different results (assuming we have more than 2 entries total)
        if total > 2:
            page1_ids = {entry.id for entry in results_page1}
            page2_ids = {entry.id for entry in results_page2}
            assert len(page1_ids.intersection(page2_ids)) == 0  # No overlap
    
    @pytest.mark.integration
    def test_real_entry_update_and_delete(self, dict_service):
        """Test updating and deleting entries with real database."""
        # Create entry
        entry = Entry(
            id_="update_test_entry",
            lexical_unit={"en": "original"},
            senses=[{
                "id": "original_sense",
                "glosses": {"en": {"text": "Original gloss"}}
            }]
        )
        dict_service.create_entry(entry)
        # Update entry
        entry.lexical_unit["en"] = "updated"
        entry.senses[0].glosses = {"en": {"text": "Updated gloss"}}
        dict_service.update_entry(entry)
        # Verify update
        updated_entry = dict_service.get_entry("update_test_entry")
        assert updated_entry.lexical_unit["en"] == "updated"
        assert updated_entry.senses[0].glosses["en"]["text"] == "Updated gloss"
        
        # Delete entry
        success = dict_service.delete_entry("update_test_entry")
        assert success
        
        # Verify deletion
        with pytest.raises(NotFoundError):
            dict_service.get_entry("update_test_entry")
    
    @pytest.mark.integration
    def test_real_statistics_and_counts(self, dict_service):
        """Test statistics functionality with real database."""
        # Get initial count
        initial_count = dict_service.get_entry_count()
        
        # Add some entries
        for i in range(3):
            entry = Entry(
                id_=f"stats_test_{i}",
                lexical_unit={"en": f"word_{i}"},
                senses=[{
                    "id": f"sense_{i}",
                    "glosses": {"en": {"text": f"Definition {i}"}}
                }]
            )
            dict_service.create_entry(entry)
        
        # Check updated count
        new_count = dict_service.get_entry_count()
        assert new_count == initial_count + 3
        
        # Test statistics
        stats = dict_service.get_statistics()
        assert "total_entries" in stats
        assert stats["total_entries"] == new_count
    
    @pytest.mark.integration
    def test_real_lift_import_export_roundtrip(self, dict_service):
        """Test LIFT import/export with real data."""
        # Create test LIFT content
        test_lift = '''<?xml version="1.0" encoding="UTF-8"?>
<lift version="0.15">
    <entry id="roundtrip_test">
        <lexical-unit>
            <form lang="en"><text>roundtrip</text></form>
            <form lang="pl"><text>podróż w obie strony</text></form>
        </lexical-unit>
        <sense id="roundtrip_sense_1">
            <gloss lang="en"><text>A journey to a place and back</text></gloss>
            <definition>
                <form lang="en"><text>A trip from one place to another and back again</text></form>
            </definition>
        </sense>
    </entry>
</lift>'''
        
        # Create temporary files
        with tempfile.NamedTemporaryFile(mode='w', suffix='.lift', delete=False, encoding='utf-8') as import_file:
            import_file.write(test_lift)
            import_path = import_file.name
        
        export_path = tempfile.mktemp(suffix='.lift')
        
        try:
            # Import the LIFT file
            result = dict_service.import_lift(import_path)
            assert result >= 1  # Should import at least 1 entry
            
            # Verify the entry was imported
            entry = dict_service.get_entry("roundtrip_test")
            assert entry is not None
            assert entry.lexical_unit["en"] == "roundtrip"
            assert entry.lexical_unit["pl"] == "podróż w obie strony"
            
            # Export to LIFT
            export_content = dict_service.export_lift()
            assert export_content is not None and len(export_content) > 0
            
            # Write export content to file for verification
            with open(export_path, 'w', encoding='utf-8') as f:
                f.write(export_content)
            
            # Verify export file exists and has content
            assert os.path.exists(export_path)
            with open(export_path, 'r', encoding='utf-8') as f:
                exported_content = f.read()
                assert "roundtrip_test" in exported_content
                assert "roundtrip" in exported_content
                
        finally:
            # Cleanup
            for path in [import_path, export_path]:
                if os.path.exists(path):
                    os.unlink(path)
    
    @pytest.mark.integration
    def test_real_error_handling(self, dict_service):
        """Test error handling with real database operations."""
        # Test creating duplicate entry
        entry = Entry(
            id_="duplicate_test",
            lexical_unit={"en": "duplicate"},
            senses=[{"id": "dup_sense", "glosses": {"en": {"text": "First"}}}]
        )
        # First creation should succeed
        dict_service.create_entry(entry)
        # Second creation should fail
        with pytest.raises(ValidationError):
            dict_service.create_entry(entry)
        # Test retrieving non-existent entry
        with pytest.raises(NotFoundError):
            dict_service.get_entry("non_existent_entry")
        
        # Test updating non-existent entry
        non_existent = Entry(
            id_="non_existent",
            lexical_unit={"en": "test"},
            senses=[{"id": "test", "glosses": {"en": {"text": "test"}}}]
        )
        with pytest.raises(NotFoundError):
            dict_service.update_entry(non_existent)
    
    @pytest.mark.integration
    def test_real_sense_operations(self, dict_service):
        """Test sense-specific operations with real database."""
        # Create entry with multiple senses
        entry = Entry(
            id_="multi_sense_test",
            lexical_unit={"en": "bank"},
            senses=[
                {
                    "id": "bank_sense_1",
                    "glosses": {"en": {"text": "Financial institution"}},
                    "definitions": {"en": {"text": "A place where money is kept and financial services are provided"}}
                },
                {
                    "id": "bank_sense_2", 
                    "glosses": {"en": {"text": "Side of a river"}},
                    "definitions": {"en": {"text": "The land alongside a river or lake"}}
                }
            ]
        )
        dict_service.create_entry(entry)
        # Retrieve and verify
        retrieved = dict_service.get_entry("multi_sense_test")
        assert len(retrieved.senses) == 2
        # Test sense access
        financial_sense = next((s for s in retrieved.senses if "Financial" in s.glosses["en"]["text"]), None)
        river_sense = next((s for s in retrieved.senses if "river" in s.glosses["en"]["text"]), None)
        assert financial_sense is not None
        assert river_sense is not None
        assert financial_sense.id == "bank_sense_1"
        assert river_sense.id == "bank_sense_2"



@pytest.mark.integration
class TestRealModelInteractions:
    """Test real model interactions without database dependencies."""
    
    @pytest.mark.integration
    def test_sense_property_setters(self):
        """Test that property setters work correctly for multilingual dicts."""
        sense = Sense(id_="test_sense")

        # Test string assignment (should create nested dict)
        sense.glosses = {"en": {"text": "Test gloss"}}
        assert sense.glosses["en"]["text"] == "Test gloss"

        sense.definitions = {"en": {"text": "Test definition"}}
        assert sense.definitions["en"]["text"] == "Test definition"

        # Test dict assignment (multiple languages)
        sense.glosses = {"pl": {"text": "Polski tekst"}, "en": {"text": "English text"}}
        assert sense.glosses["pl"]["text"] == "Polski tekst"
        assert sense.glosses["en"]["text"] == "English text"

        # Test that the structure is always {lang: {text: ...}}
        for lang, val in sense.glosses.items():
            assert isinstance(val, dict) and "text" in val
    
    @pytest.mark.integration
    def test_entry_sense_integration(self):
        """Test entry and sense object integration with multilingual dicts."""
        entry = Entry(
            id_="integration_test",
            lexical_unit={"en": "test", "pl": "test"},
            senses=[
                {
                    "id": "sense_1",
                    "glosses": {"en": {"text": "First sense"}},
                    "definitions": {"en": {"text": "First definition"}}
                },
                {
                    "id": "sense_2",
                    "glosses": {"en": {"text": "Second sense"}, "pl": {"text": "Drugi sens"}},
                    "definitions": {"en": {"text": "Second definition"}, "pl": {"text": "Druga definicja"}}
                }
            ]
        )

        # Verify senses are properly converted to objects
        assert len(entry.senses) == 2
        assert all(isinstance(sense, Sense) for sense in entry.senses)

        # Test first sense
        sense1 = entry.senses[0]
        assert sense1.id == "sense_1"
        assert sense1.glosses["en"]["text"] == "First sense"
        assert sense1.definitions["en"]["text"] == "First definition"

        # Test second sense with multiple languages
        sense2 = entry.senses[1]
        assert sense2.id == "sense_2"
        assert sense2.glosses["en"]["text"] == "Second sense"
        assert sense2.glosses["pl"]["text"] == "Drugi sens"
        assert sense2.definitions["en"]["text"] == "Second definition"
        assert sense2.definitions["pl"]["text"] == "Druga definicja"
    
    @pytest.mark.integration
    def test_entry_validation_comprehensive(self):
        """Test comprehensive entry validation."""
        # Valid entry
        valid_entry = Entry(
            id_="valid_test",
            lexical_unit={"en": "valid"},
            senses=[{"id": "valid_sense", "gloss": "Valid"}]
        )
        assert valid_entry.validate()
        
        # Entry without lexical unit
        invalid_entry1 = Entry(
            id_="invalid_1",
            senses=[{"id": "sense", "gloss": "test"}]
        )
        with pytest.raises(ValidationError) as exc_info:
            invalid_entry1.validate()
        assert "Lexical unit is required" in str(exc_info.value)
        
        # Entry with empty sense ID
        invalid_entry2 = Entry(
            id_="invalid_2",
            lexical_unit={"en": "test"},
            senses=[{"id": "", "gloss": "test"}]
        )
        with pytest.raises(ValidationError) as exc_info:
            invalid_entry2.validate()
        assert "Sense ID is required and must be non-empty" in str(exc_info.value)
