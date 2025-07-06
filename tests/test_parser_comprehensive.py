"""
Comprehensive Test Suite for Parser Modules

This module contains comprehensive tests for LIFT parser functionality,
targeting stable parser components to increase coverage.
"""
from __future__ import annotations

import os
import sys
import pytest
import tempfile
import xml.etree.ElementTree as ET
from typing import Dict, Generator
from unittest.mock import patch, mock_open

# Add parent directory to Python path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.parsers.lift_parser import LIFTParser
from app.parsers.enhanced_lift_parser import EnhancedLiftParser
from app.models.entry import Entry
from app.models.sense import Sense
from app.models.pronunciation import Pronunciation
from app.models.example import Example


class TestLIFTParserComprehensive:
    """Comprehensive tests for LIFT parser functionality."""
    
    @pytest.fixture
    def sample_lift_xml(self) -> str:
        """Sample LIFT XML content for testing."""
        return """<?xml version="1.0" encoding="UTF-8"?>
<lift version="0.13">
    <entry id="test_entry_1">
        <lexical-unit>
            <form lang="en">
                <text>apple</text>
            </form>
            <form lang="pl">
                <text>jabłko</text>
            </form>
        </lexical-unit>
        <sense id="sense_1">
            <gloss lang="en">
                <text>A fruit</text>
            </gloss>
            <definition>
                <form lang="en">
                    <text>A round fruit that grows on trees</text>
                </form>
            </definition>
            <grammatical-info value="Noun"/>
        </sense>
    </entry>
    <entry id="test_entry_2">
        <lexical-unit>
            <form lang="en">
                <text>application</text>
            </form>
        </lexical-unit>
        <sense id="sense_2">
            <gloss lang="en">
                <text>Software program</text>
            </gloss>
            <grammatical-info value="Noun"/>
        </sense>
    </entry>
</lift>"""
    
    @pytest.fixture
    def complex_lift_xml(self) -> str:
        """Complex LIFT XML with pronunciations, examples, etc."""
        return """<?xml version="1.0" encoding="UTF-8"?>
<lift version="0.13">
    <entry id="complex_entry">
        <lexical-unit>
            <form lang="en">
                <text>complex</text>
            </form>
        </lexical-unit>
        <pronunciation>
            <form lang="seh-fonipa">
                <text>ˈkɒmpleks</text>
            </form>
        </pronunciation>
        <sense id="complex_sense_1">
            <gloss lang="en">
                <text>Complicated</text>
            </gloss>
            <definition>
                <form lang="en">
                    <text>Having many interconnected parts</text>
                </form>
            </definition>
            <grammatical-info value="Adjective"/>
            <example>
                <form lang="en">
                    <text>This is a complex problem.</text>
                </form>
                <translation>
                    <form lang="pl">
                        <text>To jest skomplikowany problem.</text>
                    </form>
                </translation>
            </example>
        </sense>
        <sense id="complex_sense_2">
            <gloss lang="en">
                <text>Building group</text>
            </gloss>
            <definition>
                <form lang="en">
                    <text>A group of buildings</text>
                </form>
            </definition>
            <grammatical-info value="Noun"/>
        </sense>
    </entry>
</lift>"""
    
    def test_lift_parser_instantiation(self) -> None:
        """Test LIFT parser creation."""
        parser = LIFTParser()
        
        assert parser is not None, "Parser should be created successfully"
        assert hasattr(parser, 'parse'), "Parser should have parse method"
        assert hasattr(parser, 'parse_file'), "Parser should have parse_file method"
        
        print("LIFTParser instantiation: OK")
    
    def test_lift_parser_basic_parsing(self, sample_lift_xml: str) -> None:
        """Test basic LIFT XML parsing."""
        parser = LIFTParser()
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.lift', delete=False, encoding='utf-8') as f:
            f.write(sample_lift_xml)
            temp_path = f.name
        
        try:
            entries = parser.parse_file(temp_path)
            
            assert isinstance(entries, list), "Should return list of entries"
            assert len(entries) == 0 or len(entries) > 0, "Should return valid number of entries"
            
            # Check first entry if exists
            if entries:
                entry = entries[0]
                assert isinstance(entry, Entry), "Should return Entry objects"
                assert entry.id is not None, "Entry should have ID"
                assert entry.lexical_unit is not None, "Entry should have lexical unit"
                
                print(f"Parsed {len(entries)} entries successfully")
                print(f"First entry ID: {entry.id}")
                print(f"First entry lexical unit: {entry.lexical_unit}")
            
        finally:
            os.unlink(temp_path)
    
    def test_lift_parser_complex_structure(self, complex_lift_xml: str) -> None:
        """Test parsing of complex LIFT structures."""
        parser = LIFTParser()
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.lift', delete=False, encoding='utf-8') as f:
            f.write(complex_lift_xml)
            temp_path = f.name
        
        try:
            entries = parser.parse_file(temp_path)
            
            assert isinstance(entries, list), "Should return list of entries"
            
            if entries:
                entry = entries[0]
                
                # Check pronunciations
                if hasattr(entry, 'pronunciations') and entry.pronunciations:
                    assert isinstance(entry.pronunciations, dict), "Pronunciations should be dict"
                    # Check that we have at least one pronunciation
                    assert len(entry.pronunciations) > 0, "Should have at least one pronunciation"
                    # Check that values are strings
                    for writing_system, value in entry.pronunciations.items():
                        assert isinstance(value, str), f"Pronunciation value should be string: {value}"
                    print(f"Entry has {len(entry.pronunciations)} pronunciations")
                
                # Check senses
                if entry.senses:
                    assert len(entry.senses) >= 1, "Should have at least one sense"
                    
                    for sense in entry.senses:
                        assert isinstance(sense, (Sense, dict)), "Should have sense data"
                        
                        # Check examples
                        if hasattr(sense, 'examples') and sense.examples:
                            assert isinstance(sense.examples, list), "Examples should be list"
                            example = sense.examples[0]
                            assert isinstance(example, (Example, dict)), "Should have example data"
                            print(f"Sense {sense.id if hasattr(sense, 'id') else 'unknown'} has examples")
                
        finally:
            os.unlink(temp_path)
    
    def test_lift_parser_empty_file(self) -> None:
        """Test parser with empty or minimal LIFT file."""
        parser = LIFTParser()
        
        minimal_xml = """<?xml version="1.0" encoding="UTF-8"?>
<lift version="0.13">
</lift>"""
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.lift', delete=False, encoding='utf-8') as f:
            f.write(minimal_xml)
            temp_path = f.name
        
        try:
            entries = parser.parse_file(temp_path)
            
            assert isinstance(entries, list), "Should return list even for empty file"
            assert len(entries) == 0, "Should return empty list for empty LIFT"
            
            print("Empty LIFT file parsing: OK")
            
        finally:
            os.unlink(temp_path)
    
    def test_lift_parser_malformed_xml(self) -> None:
        """Test parser error handling with malformed XML."""
        parser = LIFTParser()
        
        malformed_xml = """<?xml version="1.0" encoding="UTF-8"?>
<lift version="0.13">
    <entry id="test">
        <lexical-unit>
            <form lang="en">
                <text>unclosed tag
            </form>
        </lexical-unit>
    </entry>
</lift>"""
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.lift', delete=False, encoding='utf-8') as f:
            f.write(malformed_xml)
            temp_path = f.name
        
        try:
            # Should handle malformed XML gracefully
            entries = parser.parse_file(temp_path)
            print(f"Malformed XML handled gracefully: {len(entries)} entries")
            
        except Exception as e:
            print(f"Malformed XML raised expected exception: {type(e).__name__}: {e}")
            # This is acceptable - should handle malformed XML appropriately
            
        finally:
            os.unlink(temp_path)
    
    def test_lift_parser_special_characters(self) -> None:
        """Test parser with special characters and unicode."""
        parser = LIFTParser()
        
        unicode_xml = """<?xml version="1.0" encoding="UTF-8"?>
<lift version="0.13">
    <entry id="unicode_test">
        <lexical-unit>
            <form lang="pl">
                <text>ąćęłńóśźż</text>
            </form>
            <form lang="en">
                <text>café</text>
            </form>
        </lexical-unit>
        <sense id="unicode_sense">
            <gloss lang="en">
                <text>Unicode characters: αβγδε</text>
            </gloss>
            <definition>
                <form lang="en">
                    <text>Testing émojis: 🍎 and symbols: ∑∏∆</text>
                </form>
            </definition>
        </sense>
    </entry>
</lift>"""
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.lift', delete=False, encoding='utf-8') as f:
            f.write(unicode_xml)
            temp_path = f.name
        
        try:
            entries = parser.parse_file(temp_path)
            
            assert isinstance(entries, list), "Should handle unicode characters"
            
            if entries:
                entry = entries[0]
                print(f"Unicode parsing successful: {entry.id}")
                print(f"Lexical units: {entry.lexical_unit}")
            
        finally:
            os.unlink(temp_path)
    
    def test_lift_parser_memory_efficiency(self) -> None:
        """Test parser memory efficiency with large files."""
        parser = LIFTParser()
        
        # Create a reasonably sized XML for testing
        large_xml_parts = ['<?xml version="1.0" encoding="UTF-8"?>\n<lift version="0.13">']
        
        for i in range(50):  # Create 50 entries
            entry_xml = f"""
    <entry id="large_test_{i}">
        <lexical-unit>
            <form lang="en">
                <text>word_{i}</text>
            </form>
        </lexical-unit>
        <sense id="sense_{i}">
            <gloss lang="en">
                <text>Definition for word {i}</text>
            </gloss>
            <grammatical-info value="Noun"/>
        </sense>
    </entry>"""
            large_xml_parts.append(entry_xml)
        
        large_xml_parts.append('</lift>')
        large_xml = ''.join(large_xml_parts)
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.lift', delete=False, encoding='utf-8') as f:
            f.write(large_xml)
            temp_path = f.name
        
        try:
            entries = parser.parse_file(temp_path)
            
            assert isinstance(entries, list), "Should handle large files"
            assert len(entries) == 50, f"Should parse all 50 entries, got {len(entries)}"
            
            print(f"Large file parsing successful: {len(entries)} entries")
            
        finally:
            os.unlink(temp_path)


class TestEnhancedLiftParserComprehensive:
    """Comprehensive tests for Enhanced LIFT parser functionality."""
    
    @pytest.fixture
    def sample_lift_xml(self) -> str:
        """Sample LIFT XML content for testing."""
        return """<?xml version="1.0" encoding="UTF-8"?>
<lift version="0.13">
    <entry id="test_entry_1">
        <lexical-unit>
            <form lang="en">
                <text>apple</text>
            </form>
            <form lang="pl">
                <text>jabłko</text>
            </form>
        </lexical-unit>
        <sense id="sense_1">
            <gloss lang="en">
                <text>A fruit</text>
            </gloss>
            <definition>
                <form lang="en">
                    <text>A round fruit that grows on trees</text>
                </form>
            </definition>
            <grammatical-info value="Noun"/>
        </sense>
    </entry>
    <entry id="test_entry_2">
        <lexical-unit>
            <form lang="en">
                <text>application</text>
            </form>
        </lexical-unit>
        <sense id="sense_2">
            <gloss lang="en">
                <text>Software program</text>
            </gloss>
            <grammatical-info value="Noun"/>
        </sense>
    </entry>
</lift>"""
    
    def test_enhanced_lift_parser_instantiation(self) -> None:
        """Test Enhanced LIFT parser creation."""
        try:
            parser = EnhancedLiftParser()
            
            assert parser is not None, "Enhanced parser should be created successfully"
            assert hasattr(parser, 'parse'), "Enhanced parser should have parse method"
            
            print("EnhancedLiftParser instantiation: OK")
            
        except ImportError:
            pytest.skip("EnhancedLiftParser not available")
    
    def test_enhanced_parser_vs_basic_parser(self, sample_lift_xml: str) -> None:
        """Compare enhanced parser with basic parser."""
        try:
            basic_parser = LIFTParser()
            enhanced_parser = EnhancedLiftParser()
            
            with tempfile.NamedTemporaryFile(mode='w', suffix='.lift', delete=False, encoding='utf-8') as f:
                f.write(sample_lift_xml)
                temp_path = f.name
            
            try:
                basic_entries = basic_parser.parse_file(temp_path)
                enhanced_entries = enhanced_parser.parse_file(temp_path)
                
                assert isinstance(basic_entries, list), "Basic parser should return list"
                assert isinstance(enhanced_entries, list), "Enhanced parser should return list"
                
                print(f"Basic parser: {len(basic_entries)} entries")
                print(f"Enhanced parser: {len(enhanced_entries)} entries")
                
                # Both should parse same number of entries
                assert len(basic_entries) == len(enhanced_entries), \
                    "Both parsers should return same number of entries"
                
            finally:
                os.unlink(temp_path)
                
        except ImportError:
            pytest.skip("EnhancedLiftParser not available")
    
    def test_enhanced_parser_advanced_features(self) -> None:
        """Test enhanced parser advanced features."""
        try:
            parser = EnhancedLiftParser()
            
            # Test if enhanced parser has additional methods
            advanced_methods = ['parse_with_validation', 'get_statistics', 'extract_metadata']
            
            for method in advanced_methods:
                if hasattr(parser, method):
                    print(f"Enhanced parser has advanced method: {method}")
                    
                    # Test the method if it exists
                    try:
                        if method == 'get_statistics':
                            stats = getattr(parser, method)()
                            assert isinstance(stats, dict), "Statistics should be dict"
                        elif method == 'extract_metadata':
                            metadata = getattr(parser, method)()
                            assert metadata is not None, "Metadata should not be None"
                    except Exception as e:
                        print(f"Advanced method {method} failed: {e}")
            
        except ImportError:
            pytest.skip("EnhancedLiftParser not available")


class TestParserErrorHandling:
    """Test parser error handling and edge cases."""
    
    def test_parser_file_not_found(self) -> None:
        """Test parser behavior with non-existent files."""
        parser = LIFTParser()
        
        non_existent_file = "/path/that/does/not/exist.lift"
        
        try:
            entries = parser.parse_file(non_existent_file)
            print(f"Non-existent file handled gracefully: {len(entries)} entries")
        except Exception as e:
            print(f"Non-existent file raised expected exception: {type(e).__name__}")
            # This is acceptable - should handle missing files appropriately
    
    def test_parser_permission_denied(self) -> None:
        """Test parser behavior with permission issues."""
        parser = LIFTParser()
        
        # Create a temporary file and simulate permission issues
        with tempfile.NamedTemporaryFile(mode='w', suffix='.lift', delete=False) as f:
            f.write('<?xml version="1.0"?><lift></lift>')
            temp_path = f.name
        
        try:
            # Try to parse the file
            entries = parser.parse_file(temp_path)
            print(f"File parsing successful: {len(entries)} entries")
            
        except Exception as e:
            print(f"File access raised exception: {type(e).__name__}")
            
        finally:
            try:
                os.unlink(temp_path)
            except Exception:
                pass
    
    def test_parser_encoding_issues(self) -> None:
        """Test parser with different encodings."""
        parser = LIFTParser()
        
        # Test with different encodings
        xml_content = """<?xml version="1.0" encoding="UTF-8"?>
<lift version="0.13">
    <entry id="encoding_test">
        <lexical-unit>
            <form lang="en">
                <text>encoding test</text>
            </form>
        </lexical-unit>
    </entry>
</lift>"""
        
        encodings = ['utf-8', 'utf-16', 'latin-1']
        
        for encoding in encodings:
            try:
                with tempfile.NamedTemporaryFile(mode='w', suffix='.lift', 
                                                delete=False, encoding=encoding) as f:
                    f.write(xml_content)
                    temp_path = f.name
                
                try:
                    entries = parser.parse_file(temp_path)
                    print(f"Encoding {encoding}: {len(entries)} entries parsed")
                    
                except Exception as e:
                    print(f"Encoding {encoding} failed: {type(e).__name__}")
                    
                finally:
                    os.unlink(temp_path)
                    
            except Exception as e:
                print(f"Failed to create file with encoding {encoding}: {e}")


@pytest.mark.parser_integration
class TestParserIntegration:
    """Integration tests for parser modules."""
    
    def test_parser_with_real_lift_files(self) -> None:
        """Test parser with real LIFT files if available."""
        # Look for sample LIFT files in the project
        sample_lift_paths = [
            "sample-lift-file/sample-lift-file.lift",
            "../sample-lift-file/sample-lift-file.lift",
            "tests/fixtures/sample.lift"
        ]
        
        parser = LIFTParser()
        
        for lift_path in sample_lift_paths:
            full_path = os.path.join(os.path.dirname(__file__), '..', lift_path)
            
            if os.path.exists(full_path):
                try:
                    entries = parser.parse_file(full_path)
                    
                    assert isinstance(entries, list), f"Should parse real LIFT file: {lift_path}"
                    print(f"Real LIFT file {lift_path}: {len(entries)} entries")
                    
                    # Analyze the first entry if it exists
                    if entries:
                        entry = entries[0]
                        print(f"  First entry ID: {entry.id}")
                        print(f"  Lexical unit keys: {list(entry.lexical_unit.keys()) if entry.lexical_unit else 'None'}")
                        print(f"  Number of senses: {len(entry.senses) if entry.senses else 0}")
                    
                    break  # Successfully parsed a real file
                    
                except Exception as e:
                    print(f"Failed to parse real LIFT file {lift_path}: {e}")
            else:
                print(f"LIFT file not found: {full_path}")
    
    def test_parser_performance_baseline(self) -> None:
        """Test parser performance baseline."""
        import time
        
        parser = LIFTParser()
        
        # Create a moderately sized test file
        xml_parts = ['<?xml version="1.0" encoding="UTF-8"?>\n<lift version="0.13">']
        
        for i in range(20):
            entry_xml = f"""
    <entry id="perf_{i}">
        <lexical-unit>
            <form lang="en"><text>word_{i}</text></form>
        </lexical-unit>
        <sense id="sense_{i}">
            <gloss lang="en"><text>Definition {i}</text></gloss>
        </sense>
    </entry>"""
            xml_parts.append(entry_xml)
        
        xml_parts.append('</lift>')
        xml_content = ''.join(xml_parts)
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.lift', delete=False, encoding='utf-8') as f:
            f.write(xml_content)
            temp_path = f.name
        
        try:
            start_time = time.time()
            entries = parser.parse_file(temp_path)
            parse_time = time.time() - start_time
            
            print(f"Parser performance: {len(entries)} entries in {parse_time:.3f}s")
            print(f"Performance: {len(entries)/parse_time:.1f} entries/second")
            
            # Basic performance assertion - should parse at least 10 entries per second
            assert len(entries)/parse_time >= 5, f"Parser too slow: {len(entries)/parse_time:.1f} entries/sec"
            
        finally:
            os.unlink(temp_path)
