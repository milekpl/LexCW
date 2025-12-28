from app.models.display_profile import DisplayProfile, ProfileElement
from app.services.css_mapping_service import CSSMappingService
from app.utils.lift_to_html_transformer import LIFTToHTMLTransformer, ElementConfig
import xml.etree.ElementTree as ET

def test_reordering_gloss_before_definition():
    """
    Test that elements are rendered in the order defined by the profile,
    not the XML order.
    """
    # XML has definition then gloss
    xml = """
    <entry id="test">
        <sense id="s1">
            <definition><form lang="en"><text>Def</text></form></definition>
            <gloss lang="en"><text>Glo</text></gloss>
        </sense>
    </entry>
    """
    
    # Profile puts gloss before definition
    # Note: We need to configure parent elements (sense) too for the transformer to work 
    # if we were using the full service, but here we can test the transformer directly 
    # or the service. Let's use the service but with a manual profile construction 
    # to be safe about how it translates to configs.
    
    # However, testing LIFTToHTMLTransformer directly gives us more control over configs.
    
    config = [
        # Parent
        ElementConfig(lift_element="sense", display_order=1, css_class="sense", display_mode="block"),
        # Children - Gloss first (order 2)
        ElementConfig(lift_element="gloss", display_order=2, css_class="gloss"),
        # Definition second (order 3)
        ElementConfig(lift_element="definition", display_order=3, css_class="definition")
    ]
    
    transformer = LIFTToHTMLTransformer()
    html = transformer.transform(xml, config)
    
    # Check that gloss content appears before definition content
    gloss_index = html.find("Glo")
    def_index = html.find("Def")
    
    assert gloss_index != -1, "Gloss not found"
    assert def_index != -1, "Definition not found"
    assert gloss_index < def_index, f"Gloss should appear before Definition, but got indices: Gloss={gloss_index}, Def={def_index}"


def test_trait_reordering():
    """
    Test that traits (domain-types) can be reordered relative to other elements.
    """
    xml = """
    <entry id="test">
        <sense id="s1">
            <definition><form lang="en"><text>Def</text></form></definition>
            <trait name="domain-type" value="physics"/>
        </sense>
    </entry>
    """
    
    # Profile puts trait (domain-type) before definition
    config = [
        ElementConfig(lift_element="sense", display_order=1, css_class="sense", display_mode="block"),
        # Trait first
        ElementConfig(lift_element="trait", display_order=2, css_class="domain", filter="domain-type"),
        # Definition second
        ElementConfig(lift_element="definition", display_order=3, css_class="definition")
    ]
    
    transformer = LIFTToHTMLTransformer()
    html = transformer.transform(xml, config)
    
    trait_index = html.find("physics")
    def_index = html.find("Def")
    
    assert trait_index != -1, "Trait value not found"
    assert def_index != -1, "Definition not found"
    assert trait_index < def_index, f"Trait should appear before Definition, but got indices: Trait={trait_index}, Def={def_index}"
