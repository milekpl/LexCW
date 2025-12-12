import pytest
from app.services.css_mapping_service import CSSMappingService
from app.models.display_profile import DisplayProfile, ProfileElement


def test_trait_display_format(tmp_path):
    """Test that traits display only the resolved value, not 'name: value'."""
    css_service = CSSMappingService(storage_path=tmp_path / "profiles.json")
    
    # Entry with a trait that should be resolved
    entry_xml = """
    <entry id="e1">
        <lexical-unit>
            <form lang="en"><text>test-word</text></form>
        </lexical-unit>
        <sense>
            <trait name="usage-type" value="british-english"/>
        </sense>
    </entry>
    """
    
    elements = [
        ProfileElement(lift_element="lexical-unit"),
        ProfileElement(lift_element="trait", config={"filter": "usage-type"})
    ]
    profile = DisplayProfile(name="Trait Test", elements=elements)
    
    html = css_service.render_entry(entry_xml, profile)
    
    # Should NOT contain "usage-type:" or "name:"
    assert "usage-type:" not in html.lower()
    assert "name:" not in html.lower()
    
    # Should contain the resolved value (or original if no range exists)
    # The value should be present without the name prefix
    assert "british-english" in html or "British English" in html


if __name__ == "__main__":
    import tempfile
    with tempfile.TemporaryDirectory() as tmpdir:
        from pathlib import Path
        test_trait_display_format(Path(tmpdir))
        print("✓ Test passed: Traits display only values")
