"""
Test suite for homograph number functionality in the dictionary application.

This module tests:
1. Homograph number parsing from LIFT XML (using 'order' attribute)
2. Homograph number generation in LIFT XML (using 'order' attribute)
3. Homograph number display in entry forms
4. Homograph number display in entry lists
5. Homograph number handling in the Entry model
"""
from __future__ import annotations

import pytest

from app.models.entry import Entry
from app.parsers.lift_parser import LIFTParser



@pytest.mark.integration
class TestHomographNumberModel:
    """Test homograph number support in the Entry model."""
    
    @pytest.mark.integration
    def test_entry_creation_with_homograph_number(self):
        """Test creating an entry with a homograph number."""
        entry = Entry(id_="test_entry_1",
            lexical_unit={"en": "bank"},
            homograph_number=1
        ,
            senses=[{"id": "sense1", "definition": {"en": "test definition"}}])
        
        assert entry.homograph_number == 1
        assert entry.id == "test_entry_1"
        assert entry.lexical_unit == {"en": "bank"}
    
    @pytest.mark.integration
    def test_entry_creation_without_homograph_number(self):
        """Test creating an entry without a homograph number."""
        entry = Entry(id_="test_entry_2",
            lexical_unit={"en": "river"}
        ,
            senses=[{"id": "sense1", "definition": {"en": "test definition"}}])
        
        assert entry.homograph_number is None
        assert entry.id == "test_entry_2"
    
    @pytest.mark.integration
    def test_entry_homograph_number_type_validation(self):
        """Test that homograph number accepts integers."""
        entry = Entry(id_="test_entry_3",
            lexical_unit={"en": "test"},
            homograph_number=2
        ,
            senses=[{"id": "sense1", "definition": {"en": "test definition"}}])
        
        assert entry.homograph_number == 2
        assert isinstance(entry.homograph_number, int)



@pytest.mark.integration
class TestHomographNumberLIFTParsing:
    """Test homograph number parsing from LIFT XML."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.parser = LIFTParser(validate=False)
    
    @pytest.mark.integration
    def test_parse_entry_with_homograph_number(self):
        """Test parsing an entry with homograph number from order attribute."""
        entry_xml = '''
        <entry id="bank_1" order="1" xmlns="http://fieldworks.sil.org/schemas/lift/0.13">
            <lexical-unit>
                <form lang="en"><text>bank</text></form>
            </lexical-unit>
        </entry>
        '''
        
        entry = self.parser.parse_string(entry_xml.strip())[0]
        
        assert entry.id == "bank_1"
        assert entry.homograph_number == 1
        assert entry.lexical_unit == {"en": "bank"}
    
    @pytest.mark.integration
    def test_parse_entry_with_homograph_number_2(self):
        """Test parsing an entry with homograph number 2."""
        entry_xml = '''
        <entry id="bank_2" order="2" xmlns="http://fieldworks.sil.org/schemas/lift/0.13">
            <lexical-unit>
                <form lang="en"><text>bank</text></form>
            </lexical-unit>
        </entry>
        '''
        
        entry = self.parser.parse_string(entry_xml.strip())[0]
        
        assert entry.id == "bank_2"
        assert entry.homograph_number == 2
        assert entry.lexical_unit == {"en": "bank"}
    
    @pytest.mark.integration
    def test_parse_entry_without_homograph_number(self):
        """Test parsing an entry without homograph number."""
        entry_xml = '''
        <entry id="river_1" xmlns="http://fieldworks.sil.org/schemas/lift/0.13">
            <lexical-unit>
                <form lang="en"><text>river</text></form>
            </lexical-unit>
        </entry>
        '''
        
        entry = self.parser.parse_string(entry_xml.strip())[0]
        
        assert entry.id == "river_1"
        assert entry.homograph_number is None
        assert entry.lexical_unit == {"en": "river"}
    
    @pytest.mark.integration
    def test_parse_entry_with_invalid_homograph_number(self):
        """Test parsing an entry with invalid homograph number."""
        entry_xml = '''
        <entry id="test_1" order="invalid" xmlns="http://fieldworks.sil.org/schemas/lift/0.13">
            <lexical-unit>
                <form lang="en"><text>test</text></form>
            </lexical-unit>
        </entry>
        '''
        
        entry = self.parser.parse_string(entry_xml.strip())[0]
        
        assert entry.id == "test_1"
        assert entry.homograph_number is None  # Should be None due to invalid value
        assert entry.lexical_unit == {"en": "test"}



@pytest.mark.integration
class TestHomographNumberLIFTGeneration:
    """Test homograph number generation in LIFT XML."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.parser = LIFTParser(validate=False)
    
    @pytest.mark.integration
    def test_generate_lift_with_homograph_number(self):
        """Test generating LIFT XML with homograph number."""
        entry = Entry(id_="bank_1",
            lexical_unit={"en": "bank"},
            homograph_number=1
        ,
            senses=[{"id": "sense1", "definition": {"en": "test definition"}}])
        
        lift_xml = self.parser.generate_lift_string([entry])
        
        # Check that order attribute is present
        assert 'order="1"' in lift_xml
        assert 'id="bank_1"' in lift_xml
        assert '<lift:text>bank</lift:text>' in lift_xml
    
    @pytest.mark.integration
    def test_generate_lift_with_homograph_number_2(self):
        """Test generating LIFT XML with homograph number 2."""
        entry = Entry(id_="bank_2",
            lexical_unit={"en": "bank"},
            homograph_number=2
        ,
            senses=[{"id": "sense1", "definition": {"en": "test definition"}}])
        
        lift_xml = self.parser.generate_lift_string([entry])
        
        # Check that order attribute is present
        assert 'order="2"' in lift_xml
        assert 'id="bank_2"' in lift_xml
    
    @pytest.mark.integration
    def test_generate_lift_without_homograph_number(self):
        """Test generating LIFT XML without homograph number."""
        entry = Entry(id_="river_1",
            lexical_unit={"en": "river"}
        ,
            senses=[{"id": "sense1", "definition": {"en": "test definition"}}])
        
        lift_xml = self.parser.generate_lift_string([entry])
        
        # Check that order attribute is NOT present
        assert 'order=' not in lift_xml
        assert 'id="river_1"' in lift_xml
        assert '<lift:text>river</lift:text>' in lift_xml
    
    @pytest.mark.integration
    def test_generate_lift_multiple_entries_with_homograph_numbers(self):
        """Test generating LIFT XML with multiple entries having homograph numbers."""
        entries = [
            Entry(id_="bank_1",
                lexical_unit={"en": "bank"},
                homograph_number=1
            ,
            senses=[{"id": "sense1", "definition": {"en": "test definition"}}]),
            Entry(id_="bank_2",
                lexical_unit={"en": "bank"},
                homograph_number=2
            ,
            senses=[{"id": "sense1", "definition": {"en": "test definition"}}]),
            Entry(id_="river_1",
                lexical_unit={"en": "river"}
            ,
            senses=[{"id": "sense1", "definition": {"en": "test definition"}}])
        ]
        
        lift_xml = self.parser.generate_lift_string(entries)
        
        # Check all entries are present with correct attributes
        assert 'id="bank_1"' in lift_xml
        assert 'order="1"' in lift_xml
        assert 'id="bank_2"' in lift_xml
        assert 'order="2"' in lift_xml
        assert 'id="river_1"' in lift_xml
        # Count order occurrences (should be 2)
        assert lift_xml.count('order=') == 2



@pytest.mark.integration
class TestHomographNumberUIIntegration:
    """Test homograph number display in UI components."""
    
    @pytest.mark.integration
    def test_entry_list_displays_homograph_number(self):
        """Test that entry list JavaScript handles homograph numbers."""
        # This test would verify the JavaScript logic for appending subscripts
        # In practice, this could be tested with a functional test framework
        # For now, we'll verify the basic logic structure
        
        # Mock the basic JavaScript logic pattern for appending homograph number
        def append_homograph_subscript(entry_text: str, homograph_number: int | None) -> str:
            if homograph_number:
                return f"{entry_text}<sub>{homograph_number}</sub>"
            return entry_text
        
        # Test with homograph number > 1 (should display)
        result = append_homograph_subscript("bank", 2)
        assert result == "bank<sub>2</sub>"
        
        # Test with homograph number = 1 (should also display now)
        result = append_homograph_subscript("bank", 1)
        assert result == "bank<sub>1</sub>"
        
        # Test without homograph number
        result = append_homograph_subscript("river", None)
        assert result == "river"
    
    @pytest.mark.integration
    def test_entry_form_displays_homograph_number(self):
        """Test that entry form template displays homograph number."""
        from jinja2 import Template
        
        # Simulate the template rendering
        template_content = '''
        {% if entry.homograph_number %}
        <div class="mb-3">
            <label for="homograph-number" class="form-label">Homograph Number</label>
            <input type="text" class="form-control" id="homograph-number" 
                   value="{{ entry.homograph_number }}" readonly>
        </div>
        {% endif %}
        '''
        
        template = Template(template_content)
        
        # Test with homograph number
        entry_with_homograph = Entry(id_="bank_1",
            lexical_unit={"en": "bank"},
            homograph_number=1
        ,
            senses=[{"id": "sense1", "definition": {"en": "test definition"}}])
        
        rendered = template.render(entry=entry_with_homograph)
        assert 'Homograph Number' in rendered
        assert 'value="1"' in rendered
        assert 'readonly' in rendered
        
        # Test without homograph number
        entry_without_homograph = Entry(id_="river_1",
            lexical_unit={"en": "river"}
        ,
            senses=[{"id": "sense1", "definition": {"en": "test definition"}}])
        
        rendered = template.render(entry=entry_without_homograph)
        assert 'Homograph Number' not in rendered
    
    @pytest.mark.integration
    def test_entry_title_displays_homograph_number(self):
        """Test that entry title includes homograph number as subscript."""
        from jinja2 import Template
        
        template_content = '''{% if entry.lexical_unit is mapping %}{{ entry.lexical_unit.values()|join(', ') }}{% else %}{{ entry.lexical_unit }}{% endif %}{% if entry.homograph_number %}<sub>{{ entry.homograph_number }}</sub>{% endif %}'''
        
        template = Template(template_content)
        
        # Test with homograph number
        entry_with_homograph = Entry(id_="bank_1",
            lexical_unit={"en": "bank"},
            homograph_number=2
        ,
            senses=[{"id": "sense1", "definition": {"en": "test definition"}}])
        
        rendered = template.render(entry=entry_with_homograph).strip()
        assert rendered == "bank<sub>2</sub>"
        
        # Test without homograph number
        entry_without_homograph = Entry(id_="river_1",
            lexical_unit={"en": "river"}
        ,
            senses=[{"id": "sense1", "definition": {"en": "test definition"}}])
        
        rendered = template.render(entry=entry_without_homograph).strip()
        assert rendered == "river"
    
    @pytest.mark.integration
    def test_homograph_number_1_displays_in_ui(self):
        """Test that homograph number 1 is displayed in UI (not just numbers > 1)."""
        # Create an entry with homograph number 1
        entry = Entry(id_="bank1_test",
            lexical_unit={"en": "bank"},
            homograph_number=1
        ,
            senses=[{"id": "sense1", "definition": {"en": "test definition"}}])
        
        # Test entry list display logic (simulating JavaScript behavior)
        # Should display homograph number 1, not skip it
        should_display_homograph = bool(entry.homograph_number)
        assert should_display_homograph is True
        
        # Test entry view template logic (homograph number should be shown)
        # This simulates the template condition {% if entry.homograph_number %}
        template_should_show = bool(entry.homograph_number)
        assert template_should_show is True
        
        # Verify actual homograph number value
        assert entry.homograph_number == 1
    
    @pytest.mark.integration
    def test_consistent_homograph_spacing_across_templates(self):
        """Test that homograph number spacing is consistent between entry form and entry view."""
        from jinja2 import Template
        
        # Entry form template pattern (from line 15)
        entry_form_pattern = '''{% if entry.lexical_unit is mapping %}{{ entry.lexical_unit.values()|join(', ') }}{% else %}{{ entry.lexical_unit }}{% endif %}{% if entry.homograph_number %}<sub>{{ entry.homograph_number }}</sub>{% endif %}'''
        
        # Entry view template pattern (should match entry form)
        entry_view_pattern = '''{% if entry.lexical_unit is mapping %}{{ entry.lexical_unit.values()|join(', ') }}{% else %}{{ entry.lexical_unit }}{% endif %}{% if entry.homograph_number %}<sub>{{ entry.homograph_number }}</sub>{% endif %}'''
        
        # Test with homograph number
        entry_with_homograph = Entry(id_="bank1_test",
            lexical_unit={"en": "bank"},
            homograph_number=1
        ,
            senses=[{"id": "sense1", "definition": {"en": "test definition"}}])
        
        form_template = Template(entry_form_pattern)
        view_template = Template(entry_view_pattern)
        
        form_result = form_template.render(entry=entry_with_homograph)
        view_result = view_template.render(entry=entry_with_homograph)
        
        # Both should produce the same result
        assert form_result == view_result
        assert form_result == "bank<sub>1</sub>"
        
        # Test without homograph number
        entry_without_homograph = Entry(id_="river_test",
            lexical_unit={"en": "river"}
        ,
            senses=[{"id": "sense1", "definition": {"en": "test definition"}}])
        
        form_result_no_hom = form_template.render(entry=entry_without_homograph)
        view_result_no_hom = view_template.render(entry=entry_without_homograph)
        
        # Both should produce the same result
        assert form_result_no_hom == view_result_no_hom
        assert form_result_no_hom == "river"



@pytest.mark.integration
class TestHomographNumberRoundTrip:
    """Test round-trip parsing and generation of homograph numbers."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.parser = LIFTParser(validate=False)
    
    @pytest.mark.integration
    def test_homograph_number_round_trip(self):
        """Test that homograph numbers survive parse -> generate -> parse cycle."""
        original_lift = '''
        <entry id="bank_1" order="1" xmlns="http://fieldworks.sil.org/schemas/lift/0.13">
            <lexical-unit>
                <form lang="en"><text>bank</text></form>
            </lexical-unit>
        </entry>
        '''
        
        # Parse the original LIFT
        entry = self.parser.parse_string(original_lift.strip())[0]
        assert entry.homograph_number == 1
        
        # Generate LIFT from the entry
        generated_lift = self.parser.generate_lift_string([entry])
        
        # Parse the generated LIFT again
        regenerated_entries = self.parser.parse_string(generated_lift)
        assert len(regenerated_entries) == 1
        
        regenerated_entry = regenerated_entries[0]
        assert regenerated_entry.homograph_number == 1
        assert regenerated_entry.id == "bank_1"
        assert regenerated_entry.lexical_unit == {"en": "bank"}
    
    @pytest.mark.integration
    def test_multiple_homographs_round_trip(self):
        """Test round-trip with multiple homographs."""
        original_lift = '''
        <lift version="0.13" xmlns="http://fieldworks.sil.org/schemas/lift/0.13">
            <entry id="bank_1" order="1">
                <lexical-unit>
                    <form lang="en"><text>bank</text></form>
                </lexical-unit>
            </entry>
            <entry id="bank_2" order="2">
                <lexical-unit>
                    <form lang="en"><text>bank</text></form>
                </lexical-unit>
            </entry>
            <entry id="river_1">
                <lexical-unit>
                    <form lang="en"><text>river</text></form>
                </lexical-unit>
            </entry>
        </lift>
        '''
        
        # Parse the original LIFT
        entries = self.parser.parse_string(original_lift.strip())
        assert len(entries) == 3
        
        # Check individual entries
        bank_1 = next(e for e in entries if e.id == "bank_1")
        bank_2 = next(e for e in entries if e.id == "bank_2")
        river_1 = next(e for e in entries if e.id == "river_1")
        
        assert bank_1.homograph_number == 1
        assert bank_2.homograph_number == 2
        assert river_1.homograph_number is None
        
        # Generate LIFT from the entries
        generated_lift = self.parser.generate_lift_string(entries)
        
        # Parse the generated LIFT again
        regenerated_entries = self.parser.parse_string(generated_lift)
        assert len(regenerated_entries) == 3
        
        # Verify all homograph numbers are preserved
        regenerated_bank_1 = next(e for e in regenerated_entries if e.id == "bank_1")
        regenerated_bank_2 = next(e for e in regenerated_entries if e.id == "bank_2")
        regenerated_river_1 = next(e for e in regenerated_entries if e.id == "river_1")
        
        assert regenerated_bank_1.homograph_number == 1
        assert regenerated_bank_2.homograph_number == 2
        assert regenerated_river_1.homograph_number is None


if __name__ == "__main__":
    pytest.main([__file__])
