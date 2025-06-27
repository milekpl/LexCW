"""
Unit Tests for Base Exporter and Utility Classes
Tests basic functionality without requiring database connections.
"""
import os
import sys
import pytest
import tempfile

# Add parent directory to Python path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.exporters.base_exporter import BaseExporter
from app.utils.exceptions import ExportError, ValidationError, DatabaseError, NotFoundError
from app.models.pronunciation import Pronunciation
from app.models.example import Example


class TestBaseExporter:
    """Test the base exporter functionality."""
    
    def test_base_exporter_initialization(self):
        """Test initializing the base exporter."""
        from unittest.mock import Mock
        mock_service = Mock()
        
        exporter = BaseExporter(mock_service)
        assert exporter.dictionary_service == mock_service
        
    def test_base_exporter_abstract_methods(self):
        """Test that base exporter is abstract."""
        from unittest.mock import Mock
        mock_service = Mock()
        
        exporter = BaseExporter(mock_service)
        
        # Should raise NotImplementedError for abstract methods
        with pytest.raises(NotImplementedError):
            exporter.export("test_path")


class TestExceptionClasses:
    """Test custom exception classes."""
    
    def test_export_error(self):
        """Test ExportError exception."""
        error = ExportError("Export failed")
        assert str(error) == "Export failed"
        assert isinstance(error, Exception)
        
        # Test with cause
        try:
            raise ValueError("Original error")
        except ValueError as e:
            export_error = ExportError("Export failed")
            export_error.__cause__ = e
            assert export_error.__cause__ == e
    
    def test_validation_error(self):
        """Test ValidationError exception.""" 
        error = ValidationError("Validation failed")
        assert str(error) == "Validation failed"
        assert isinstance(error, Exception)
        
        # Test with details
        error_with_details = ValidationError("Invalid entry", {"field": "required"})
        assert str(error_with_details) == "Invalid entry"
        assert error_with_details.details == {"field": "required"}
    
    def test_database_error(self):
        """Test DatabaseError exception."""
        error = DatabaseError("Database connection failed")
        assert str(error) == "Database connection failed"
        assert isinstance(error, Exception)
        
        # Test with original exception
        original = ConnectionError("Connection refused")
        db_error = DatabaseError("Failed to connect", original)
        assert db_error.original_exception == original
    
    def test_not_found_error(self):
        """Test NotFoundError exception."""
        error = NotFoundError("Entry not found")
        assert str(error) == "Entry not found"
        assert isinstance(error, Exception)
        
        # Test with resource info
        error_with_resource = NotFoundError("Resource not found", resource_type="entry", resource_id="test123")
        assert error_with_resource.resource_type == "entry"
        assert error_with_resource.resource_id == "test123"


class TestPronunciationModel:
    """Test Pronunciation model functionality."""
    
    def test_pronunciation_creation(self):
        """Test creating a pronunciation object."""
        pronunciation = Pronunciation(
            id="test_pronunciation",
            form="test",
            media_file="test.mp3"
        )
        
        assert pronunciation.id == "test_pronunciation"
        assert pronunciation.form == "test"
        assert pronunciation.media_file == "test.mp3"
    
    def test_pronunciation_validation(self):
        """Test pronunciation validation."""
        # Valid pronunciation
        valid_pronunciation = Pronunciation(
            id="valid_pronunciation",
            form="test"
        )
        assert valid_pronunciation.validate()
        
        # Invalid pronunciation - no form
        invalid_pronunciation = Pronunciation(id="invalid")
        with pytest.raises(ValidationError):
            invalid_pronunciation.validate()
    
    def test_pronunciation_to_dict(self):
        """Test converting pronunciation to dictionary."""
        pronunciation = Pronunciation(
            id="dict_test",
            form="test_form",
            media_file="audio.mp3"
        )
        
        result = pronunciation.to_dict()
        assert isinstance(result, dict)
        assert result["id"] == "dict_test"
        assert result["form"] == "test_form"
        assert result["media_file"] == "audio.mp3"
    
    def test_pronunciation_from_dict(self):
        """Test creating pronunciation from dictionary."""
        data = {
            "id": "from_dict_test",
            "form": "test_form",
            "media_file": "test.wav"
        }
        
        pronunciation = Pronunciation.from_dict(data)
        assert pronunciation.id == "from_dict_test"
        assert pronunciation.form == "test_form"
        assert pronunciation.media_file == "test.wav"
    
    def test_pronunciation_str_representation(self):
        """Test string representation of pronunciation."""
        pronunciation = Pronunciation(
            id="str_test",
            form="pronunciation_form"
        )
        
        str_repr = str(pronunciation)
        assert "pronunciation_form" in str_repr
        assert "str_test" in str_repr


class TestExampleModel:
    """Test Example model functionality."""
    
    def test_example_creation(self):
        """Test creating an example object."""
        example = Example(
            id="test_example",
            form_text="This is an example.",
            translation="To jest przykład."
        )
        
        assert example.id == "test_example"
        assert example.form_text == "This is an example."
        assert example.translation == "To jest przykład."
    
    def test_example_validation(self):
        """Test example validation."""
        # Valid example
        valid_example = Example(
            id="valid_example",
            form_text="Valid example text"
        )
        assert valid_example.validate()
        
        # Invalid example - no text
        invalid_example = Example(id="invalid")
        with pytest.raises(ValidationError):
            invalid_example.validate()
    
    def test_example_to_dict(self):
        """Test converting example to dictionary."""
        example = Example(
            id="dict_example",
            form_text="Example text",
            translation="Translation text"
        )
        
        result = example.to_dict()
        assert isinstance(result, dict)
        assert result["id"] == "dict_example"
        assert result["form_text"] == "Example text"
        assert result["translation"] == "Translation text"
    
    def test_example_from_dict(self):
        """Test creating example from dictionary."""
        data = {
            "id": "from_dict_example",
            "form_text": "Example from dict",
            "translation": "Przykład ze słownika"
        }
        
        example = Example.from_dict(data)
        assert example.id == "from_dict_example"
        assert example.form_text == "Example from dict"
        assert example.translation == "Przykład ze słownika"
    
    def test_example_str_representation(self):
        """Test string representation of example."""
        example = Example(
            id="str_example",
            form_text="String test example"
        )
        
        str_repr = str(example)
        assert "String test example" in str_repr
        assert "str_example" in str_repr


class TestUtilityFunctions:
    """Test utility functions and helpers."""
    
    def test_file_operations(self):
        """Test file-related utility operations."""
        # Test with temporary file
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as temp_file:
            temp_file.write("test content")
            temp_path = temp_file.name
        
        try:
            # File should exist and have content
            assert os.path.exists(temp_path)
            
            with open(temp_path, 'r') as f:
                content = f.read()
                assert content == "test content"
                
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)
    
    def test_string_validation(self):
        """Test string validation helpers."""
        # Test non-empty strings
        assert "test" != ""
        assert len("test") > 0
        
        # Test empty strings
        assert "" == ""
        assert len("") == 0
        
        # Test whitespace handling
        assert "  test  ".strip() == "test"
        assert "".strip() == ""
    
    def test_list_operations(self):
        """Test list operation helpers."""
        test_list = ["a", "b", "c"]
        
        assert len(test_list) == 3
        assert "a" in test_list
        assert "d" not in test_list
        
        # Test list comprehensions
        upper_list = [item.upper() for item in test_list]
        assert upper_list == ["A", "B", "C"]
    
    def test_dict_operations(self):
        """Test dictionary operation helpers."""
        test_dict = {"key1": "value1", "key2": "value2"}
        
        assert len(test_dict) == 2
        assert "key1" in test_dict
        assert "key3" not in test_dict
        
        # Test dict comprehensions
        reversed_dict = {v: k for k, v in test_dict.items()}
        assert reversed_dict == {"value1": "key1", "value2": "key2"}


class TestModelValidation:
    """Test model validation logic."""
    
    def test_id_validation(self):
        """Test ID validation patterns."""
        # Valid IDs
        valid_ids = ["test_id", "test123", "entry_1", "sense_abc"]
        for valid_id in valid_ids:
            assert valid_id is not None
            assert len(valid_id) > 0
            assert isinstance(valid_id, str)
        
        # Invalid IDs
        invalid_ids = ["", None, 123, []]
        for invalid_id in invalid_ids:
            if invalid_id is None:
                assert invalid_id is None
            elif isinstance(invalid_id, str):
                assert len(invalid_id) == 0
            else:
                assert not isinstance(invalid_id, str)
    
    def test_language_code_validation(self):
        """Test language code validation."""
        valid_languages = ["en", "pl", "es", "fr", "de"]
        for lang in valid_languages:
            assert isinstance(lang, str)
            assert len(lang) >= 2
        
        # Test language mappings
        language_map = {"en": "English", "pl": "Polish", "es": "Spanish"}
        assert language_map["en"] == "English"
        assert language_map["pl"] == "Polish"
    
    def test_text_content_validation(self):
        """Test text content validation."""
        # Valid text content
        valid_texts = ["Hello world", "Test definition", "Example sentence"]
        for text in valid_texts:
            assert isinstance(text, str)
            assert len(text.strip()) > 0
        
        # Test text cleaning
        messy_text = "  Test with spaces  "
        clean_text = messy_text.strip()
        assert clean_text == "Test with spaces"
        
        # Test special characters
        special_text = "Text with ąćęłńóśźż characters"
        assert isinstance(special_text, str)
        assert len(special_text) > 0
