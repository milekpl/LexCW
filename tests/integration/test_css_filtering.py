
import pytest
from app.services.css_mapping_service import CSSMappingService
from app.models.display_profile import DisplayProfile, ProfileElement

class TestCSSFiltering:
    
    @pytest.fixture
    def css_service(self, tmp_path):
        return CSSMappingService(storage_path=tmp_path / "profiles.json")
    
    @pytest.fixture
    def entry_xml(self):
        return """
        <entry id="e1">
            <lexical-unit>
                <form lang="en"><text>filter-test</text></form>
            </lexical-unit>
            <relation type="_component_lexeme" ref="e2"/>
            <relation type="synonym" ref="e3"/>
            <relation type="antonym" ref="e4"/>
            <sense>
                <trait name="domain-type" value="chemistry"/>
                <trait name="semantic-domain" value="science"/>
                <field type="usage">
                    <form lang="en"><text>slang</text></form>
                </field>
                <field type="note">
                    <form lang="en"><text>general note</text></form>
                </field>
            </sense>
        </entry>
        """

    def test_relation_filter_exclude(self, css_service, entry_xml):
        """Test excluding specific relations (e.g., _component_lexeme)."""
        elements = [
            ProfileElement(lift_element="lexical-unit"),
            ProfileElement(lift_element="relation", config={"filter": "!_component_lexeme"})
        ]
        profile = DisplayProfile(name="Exclude Test", elements=elements)
        
        html = css_service.render_entry(entry_xml, profile)
        
        # component_lexeme should be hidden
        assert "_component_lexeme" not in html
        # synonym and antonym should be visible
        assert "synonym" in html
        assert "antonym" in html

    def test_relation_filter_include(self, css_service, entry_xml):
        """Test including only specific relations."""
        elements = [
            ProfileElement(lift_element="lexical-unit"),
            ProfileElement(lift_element="relation", config={"filter": "synonym"})
        ]
        profile = DisplayProfile(name="Include Test", elements=elements)
        
        html = css_service.render_entry(entry_xml, profile)
        
        # only synonym should be visible
        assert "synonym" in html
        assert "_component_lexeme" not in html
        assert "antonym" not in html
        
    def test_trait_filter(self, css_service, entry_xml):
        """Test filtering traits by name."""
        elements = [
            ProfileElement(lift_element="lexical-unit"),
            ProfileElement(lift_element="trait", config={"filter": "domain-type"})
        ]
        profile = DisplayProfile(name="Trait Test", elements=elements)
        
        html = css_service.render_entry(entry_xml, profile)
        
        assert "domain-type" in html
        assert "chemistry" in html
        # semantic-domain should be hidden
        assert "semantic-domain" not in html
        assert "science" not in html

    def test_field_filter(self, css_service, entry_xml):
        """Test filtering fields by type."""
        elements = [
            ProfileElement(lift_element="lexical-unit"),
            ProfileElement(lift_element="field", config={"filter": "usage"})
        ]
        profile = DisplayProfile(name="Field Test", elements=elements)
        
        html = css_service.render_entry(entry_xml, profile)
        
        assert "usage" in html or "slang" in html
        assert "note" not in html
        assert "general note" not in html
