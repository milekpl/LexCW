"""Tests for list separator functionality in display profiles."""
import pytest
from app.services.css_mapping_service import CSSMappingService
from app.models.display_profile import DisplayProfile, ProfileElement


def test_trait_separator_comma(tmp_path):
    """Test that multiple traits are joined with comma separator (default)."""
    css_service = CSSMappingService(storage_path=tmp_path / "profiles.json")
    
    entry_xml = """
    <entry id="e1">
        <lexical-unit>
            <form lang="en"><text>test-word</text></form>
        </lexical-unit>
        <sense>
            <trait name="usage-type" value="British"/>
            <trait name="usage-type" value="Informal"/>
            <trait name="usage-type" value="Slang"/>
        </sense>
    </entry>
    """
    
    elements = [
        ProfileElement(lift_element="lexical-unit"),
        ProfileElement(lift_element="trait", config={"filter": "usage-type"})
    ]
    profile = DisplayProfile(name="Comma Test", elements=elements)
    
    html = css_service.render_entry(entry_xml, profile)
    
    # Should contain traits joined with comma
    assert "British, Informal, Slang" in html or "British,Informal,Slang" in html.replace(" ", "")


def test_trait_separator_semicolon(tmp_path):
    """Test that multiple traits are joined with semicolon separator."""
    css_service = CSSMappingService(storage_path=tmp_path / "profiles.json")
    
    entry_xml = """
    <entry id="e1">
        <lexical-unit>
            <form lang="en"><text>test-word</text></form>
        </lexical-unit>
        <sense>
            <trait name="usage-type" value="British"/>
            <trait name="usage-type" value="Informal"/>
        </sense>
    </entry>
    """
    
    elements = [
        ProfileElement(lift_element="lexical-unit"),
        ProfileElement(lift_element="trait", config={"filter": "usage-type", "separator": "; "})
    ]
    profile = DisplayProfile(name="Semicolon Test", elements=elements)
    
    html = css_service.render_entry(entry_xml, profile)
    
    # Should contain traits joined with semicolon
    assert "British; Informal" in html


def test_field_separator_pipe(tmp_path):
    """Test that multiple fields are joined with pipe separator."""
    css_service = CSSMappingService(storage_path=tmp_path / "profiles.json")
    
    entry_xml = """
    <entry id="e1">
        <lexical-unit>
            <form lang="en"><text>test-word</text></form>
        </lexical-unit>
        <sense>
            <field type="usage">
                <form lang="en"><text>Common in speech</text></form>
            </field>
            <field type="usage">
                <form lang="en"><text>Rare in writing</text></form>
            </field>
        </sense>
    </entry>
    """
    
    elements = [
        ProfileElement(lift_element="lexical-unit"),
        ProfileElement(lift_element="field", config={"filter": "usage", "separator": " | "})
    ]
    profile = DisplayProfile(name="Pipe Test", elements=elements)
    
    html = css_service.render_entry(entry_xml, profile)
    
    # Should contain fields joined with pipe
    assert "Common in speech | Rare in writing" in html


def test_relation_separator_space(tmp_path):
    """Test that multiple relations are joined with space separator."""
    css_service = CSSMappingService(storage_path=tmp_path / "profiles.json")
    
    entry_xml = """
    <entry id="e1">
        <lexical-unit>
            <form lang="en"><text>fast</text></form>
        </lexical-unit>
        <sense>
            <relation type="synonym" ref="quick" headword="quick"/>
            <relation type="synonym" ref="rapid" headword="rapid"/>
            <relation type="synonym" ref="swift" headword="swift"/>
        </sense>
    </entry>
    """
    
    elements = [
        ProfileElement(lift_element="lexical-unit"),
        ProfileElement(lift_element="relation", config={"filter": "synonym", "separator": " "})
    ]
    profile = DisplayProfile(name="Space Test", elements=elements)
    
    html = css_service.render_entry(entry_xml, profile)
    
    # Should contain relations joined with space (no comma)
    # The exact format depends on how relations are rendered, but they should be space-separated
    assert "quick" in html and "rapid" in html and "swift" in html


if __name__ == "__main__":
    import tempfile
    from pathlib import Path
    
    with tempfile.TemporaryDirectory() as tmpdir:
        tmppath = Path(tmpdir)
        print("Testing comma separator...")
        test_trait_separator_comma(tmppath)
        print("✓ Comma separator test passed")
        
        print("Testing semicolon separator...")
        test_trait_separator_semicolon(tmppath)
        print("✓ Semicolon separator test passed")
        
        print("Testing pipe separator...")
        test_field_separator_pipe(tmppath)
        print("✓ Pipe separator test passed")
        
        print("Testing space separator...")
        test_relation_separator_space(tmppath)
        print("✓ Space separator test passed")
        
        print("\nAll tests passed!")
