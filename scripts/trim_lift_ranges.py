"""
Script to trim a LIFT .lift-ranges file to a minimal, universal set of values for each range.
- Retains all semantic domains.
- For grammatical-info, retains universal POS (Noun, Verb, Adjective, Adverb, Pronoun, Pro-form, Abbreviation, Acronym, etc.), excludes countability distinctions and project-specific subtypes.
- Retains recommended etymology, variant-types, complex-form-types.
- Can be extended for other ranges.
"""
import xml.etree.ElementTree as ET
from typing import Set

# Universal grammatical-info values to include (updated according to recommendations)
UNIVERSAL_POS = {
    "Noun", "Proper Noun", "Verb", "Auxiliary Verb", "Adjective", "Adverb", 
    "Pronoun", "Preposition", "Adposition", "Conjunction", "Coordinating Conjunction", 
    "Subordinating Conjunction", "Interjection", "Particle", "Determiner", "Article", 
    "Numeral", "Abbreviation", "Acronym"
}

# Complex form types to include (from SIL Fieldworks)
COMPLEX_FORM_TYPES = {
    "Compound", "Derivative", "Idiom", "Phrasal Verb", "Contraction", "Saying"
}

# Variant types to include (from SIL Fieldworks)
VARIANT_TYPES = {
    "Dialectal Variant", "Free Variant", "Irregularly Inflected Form", "Spelling Variant"
}

# Lexical relations to include (updated according to recommendations)
RECOMMENDED_LEXICAL_RELATIONS = {
    "Part", "Whole", "Specific", "Generic", "Synonym", "Antonym", "Troponym", "Compare"
}

# Usage labels to include
USAGE_LABELS = {
    # Domain labels
    "Anatomy", "Computer Science", "Mathematics", "Medicine", "Physics", 
    # Regional labels  
    "British English", "American English", "Australian English", "Canadian English",
    # Register labels
    "Formal", "Informal", "Colloquial", "Poetic", "Technical", "Slang",
    # Usage/Sociolinguistic labels
    "Offensive", "Taboo", "Vulgar", "Euphemistic", "Politically Correct",
    # Temporal labels
    "Archaic", "Obsolete", "Neologism", "Modern", "Historical"
}

# Project-specific substrings to exclude (for countability etc.)
EXCLUDE_SUBSTRINGS = {"Countable", "Uncountable", "[C]", "[U]", "[C/N]"}

# Ranges to always retain all values
ALWAYS_INCLUDE_RANGES = {"semantic-domain-ddp4", "semantic-domain"}

# Input/output paths
INPUT_PATH = "minimal/empty.lift-ranges"
OUTPUT_PATH = "config/minimal.lift-ranges"

def should_include_gram_info(elem: ET.Element) -> bool:
    label = elem.findtext("label/form/text")
    if not label:
        return False
    if label in UNIVERSAL_POS:
        return True
    # Check for exclusion substrings
    for excl in EXCLUDE_SUBSTRINGS:
        if excl in label:
            return False
    return False

def should_include_complex_form(elem: ET.Element) -> bool:
    """Include recommended complex form types."""
    label = elem.findtext("label/form/text")
    if not label:
        return False
    return label in COMPLEX_FORM_TYPES

def should_include_lexical_relation(elem: ET.Element) -> bool:
    """Include recommended lexical relations."""
    label = elem.findtext("label/form/text")
    if not label:
        return False
    # Exclude Calendar as per recommendations
    if label == "Calendar":
        return False
    return label in RECOMMENDED_LEXICAL_RELATIONS

def should_include_variant_type(elem: ET.Element) -> bool:
    """Include recommended variant types."""
    label = elem.findtext("label/form/text")
    if not label:
        return False
    return label in VARIANT_TYPES

def create_usage_labels_range(root: ET.Element):
    """Create a new range for usage labels."""
    usage_labels_range = ET.SubElement(root, "range", id="usage-labels")
    
    # Define recommended usage labels
    usage_labels = [
        ("Domain", "domain", "Marks terms belonging to specialized fields."),
        ("Regional", "regional", "Indicates spatial distribution."),
        ("Register", "register", "Indicates stylistic level."),
        ("Usage", "usage", "Marks words that are offensive, taboo, or limited to specific text types."),
        ("Temporal", "temporal", "Identifies archaic, obsolete, or new (neologism) words.")
    ]
    
    for label, abbrev, descr in usage_labels:
        range_elem = ET.SubElement(usage_labels_range, "range-element", id=label.lower().replace(" ", "-"))
        label_elem = ET.SubElement(range_elem, "label")
        form_elem = ET.SubElement(label_elem, "form", lang="en")
        ET.SubElement(form_elem, "text").text = label
        
        abbrev_elem = ET.SubElement(range_elem, "abbrev")
        form_elem = ET.SubElement(abbrev_elem, "form", lang="en")
        ET.SubElement(form_elem, "text").text = abbrev
        
        descr_elem = ET.SubElement(range_elem, "description")
        form_elem = ET.SubElement(descr_elem, "form", lang="en")
        ET.SubElement(form_elem, "text").text = descr

def create_complex_form_types_range(root: ET.Element):
    """Create a new range for complex form types."""
    complex_form_range = ET.SubElement(root, "range", id="complex-form-types")
    
    # Define recommended complex form types
    complex_forms = [
        ("Compound", "comp", "A stem made of more than one root."),
        ("Derivative", "der", "A stem made up of a root plus an affix that adds a non-inflectional component of meaning."),
        ("Idiom", "id", "A multi-word expression that is recognized as a semantic unit."),
        ("Phrasal Verb", "ph. v.", "A combination of a lexical verb and a verbal particle that forms a single semantic and syntactic unit."),
        ("Contraction", "contr.", "A combination of two lexemes that are phonologically reduced."),
        ("Saying", "say.", "Any pithy phrasal expression of wisdom or truth; esp., an adage, proverb, or maxim.")
    ]
    
    for label, abbrev, descr in complex_forms:
        range_elem = ET.SubElement(complex_form_range, "range-element", id=label.lower().replace(" ", "-"))
        label_elem = ET.SubElement(range_elem, "label")
        form_elem = ET.SubElement(label_elem, "form", lang="en")
        ET.SubElement(form_elem, "text").text = label
        
        abbrev_elem = ET.SubElement(range_elem, "abbrev")
        form_elem = ET.SubElement(abbrev_elem, "form", lang="en")
        ET.SubElement(form_elem, "text").text = abbrev
        
        descr_elem = ET.SubElement(range_elem, "description")
        form_elem = ET.SubElement(descr_elem, "form", lang="en")
        ET.SubElement(form_elem, "text").text = descr

def add_missing_pos_categories(root: ET.Element):
    """Add missing POS categories to grammatical-info range."""
    gram_info_range = root.find("range[@id='grammatical-info']")
    if gram_info_range is None:
        return
    
    # List of missing POS categories to add
    missing_pos = [
        ("Proper Noun", "propn", "A noun that denotes a particular person, place, or thing.", "ProperNoun"),
        ("Auxiliary Verb", "aux", "A verb that adds functional or grammatical meaning to the clause.", "Auxiliary"),
        ("Adposition", "adp", "A word that expresses spatial or temporal relations (covers both prepositions and postpositions).", "Adposition"),
        ("Coordinating Conjunction", "cc", "A conjunction that links words, phrases, or clauses of equal syntactic importance.", "Conjunction-Coordinating"),
        ("Subordinating Conjunction", "sc", "A conjunction that introduces a dependent clause and indicates its relation to the rest of the sentence.", "Conjunction-Subordinating"),
        ("Article", "art", "A word that combines with a noun to indicate the type of reference being made.", "Article"),
        ("Particle", "part", "A word that does not belong to the major parts of speech but has grammatical function.", "Particle"),
        ("Numeral", "num", "A word that expresses a number or quantity.", "Numeral"),
        ("Abbreviation", "abbr", "A shortened form of a word or phrase.", "Abbreviation"),
        ("Acronym", "acr", "A word formed from the initial letters of a multi-word name.", "Acronym")
    ]
    
    # Check which POS categories are already present
    existing_pos = set()
    for elem in gram_info_range.findall("range-element"):
        label = elem.findtext("label/form/text")
        if label:
            existing_pos.add(label)
    
    # Add missing POS categories
    for label, abbrev, descr, catalog_id in missing_pos:
        if label not in existing_pos:
            range_elem = ET.SubElement(gram_info_range, "range-element", id=label.replace(" ", "-"))
            label_elem = ET.SubElement(range_elem, "label")
            form_elem = ET.SubElement(label_elem, "form", lang="en")
            ET.SubElement(form_elem, "text").text = label
            
            abbrev_elem = ET.SubElement(range_elem, "abbrev")
            form_elem = ET.SubElement(abbrev_elem, "form", lang="en")
            ET.SubElement(form_elem, "text").text = abbrev
            
            descr_elem = ET.SubElement(range_elem, "description")
            form_elem = ET.SubElement(descr_elem, "form", lang="en")
            ET.SubElement(form_elem, "text").text = descr
            
            ET.SubElement(range_elem, "trait", name="catalog-source-id", value=catalog_id)

def add_component_lexeme_relation(root: ET.Element):
    """Add the special _component-lexeme relation for complex forms."""
    lexical_relation_range = root.find("range[@id='lexical-relation']")
    if lexical_relation_range is None:
        return
    
    # Check if _component-lexeme already exists
    for elem in lexical_relation_range.findall("range-element"):
        elem_id = elem.get("id")
        if elem_id == "_component-lexeme":
            return  # Already exists
    
    # Add the _component-lexeme relation
    range_elem = ET.SubElement(lexical_relation_range, "range-element", 
                              id="_component-lexeme", 
                              guid="4e1c72b2-7430-4eb9-a9d2-4b31c5620804")
    
    label_elem = ET.SubElement(range_elem, "label")
    form_elem = ET.SubElement(label_elem, "form", lang="en")
    ET.SubElement(form_elem, "text").text = "Component lexeme"
    
    abbrev_elem = ET.SubElement(range_elem, "abbrev")
    form_elem = ET.SubElement(abbrev_elem, "form", lang="en")
    ET.SubElement(form_elem, "text").text = "comp"
    
    descr_elem = ET.SubElement(range_elem, "description")
    form_elem = ET.SubElement(descr_elem, "form", lang="en")
    ET.SubElement(form_elem, "text").text = "Marks component lexemes that are primary for generating subentries"
    
    ET.SubElement(range_elem, "trait", name="referenceType", value="3")

def create_variant_types_range(root: ET.Element):
    """Create a new range for variant types."""
    variant_range = ET.SubElement(root, "range", id="variant-type")
    
    # Define recommended variant types
    variants = [
        ("Dialectal Variant", "dialectal", "Characteristically used by a specific demographic or geographic subset."),
        ("Free Variant", "free", "Interchangeable forms used by the same speaker without discernible conditioning."),
        ("Irregularly Inflected Form", "irregular", "Forms that deviate from standard inflectional rules."),
        ("Spelling Variant", "spelling", "Purely orthographic differences (e.g., color vs. colour).")
    ]
    
    for label, variant_id, descr in variants:
        range_elem = ET.SubElement(variant_range, "range-element", id=variant_id)
        label_elem = ET.SubElement(range_elem, "label")
        form_elem = ET.SubElement(label_elem, "form", lang="en")
        ET.SubElement(form_elem, "text").text = label
        
        descr_elem = ET.SubElement(range_elem, "description")
        form_elem = ET.SubElement(descr_elem, "form", lang="en")
        ET.SubElement(form_elem, "text").text = descr

def create_traits_range(root: ET.Element):
    """Create a new range for recommended traits."""
    traits_range = ET.SubElement(root, "range", id="recommended-traits")
    
    # Define recommended traits
    traits = [
        ("Catalog-Source-ID", "catalog-source-id", "Links a project-specific category to a global standard."),
        ("Inflectable-Feature", "inflectable-feature", "Marks whether a POS can take inflectional affixes."),
        ("Leading-Symbol", "leading-symbol", "Automates formatting for bound forms (e.g., adding a hyphen)."),
        ("Trailing-Symbol", "trailing-symbol", "Automates formatting for bound forms (e.g., adding a hyphen).")
    ]
    
    for label, trait_name, descr in traits:
        range_elem = ET.SubElement(traits_range, "range-element", id=trait_name)
        label_elem = ET.SubElement(range_elem, "label")
        form_elem = ET.SubElement(label_elem, "form", lang="en")
        ET.SubElement(form_elem, "text").text = label
        
        descr_elem = ET.SubElement(range_elem, "description")
        form_elem = ET.SubElement(descr_elem, "form", lang="en")
        ET.SubElement(form_elem, "text").text = descr
        
        ET.SubElement(range_elem, "trait", name="trait-name", value=trait_name)

def trim_lift_ranges(input_path: str, output_path: str):
    tree = ET.parse(input_path)
    root = tree.getroot()
    for range_elem in root.findall("range"):
        range_id = range_elem.get("id")
        if range_id in ALWAYS_INCLUDE_RANGES:
            continue  # retain all values
        if range_id == "grammatical-info":
            # Remove non-universal POS
            for elem in list(range_elem.findall("range-element")):
                if not should_include_gram_info(elem):
                    range_elem.remove(elem)
        elif range_id == "complex-form-types":
            # Keep only recommended complex form types
            for elem in list(range_elem.findall("range-element")):
                if not should_include_complex_form(elem):
                    range_elem.remove(elem)
        elif range_id == "lexical-relation":
            # Keep only recommended lexical relations
            for elem in list(range_elem.findall("range-element")):
                if not should_include_lexical_relation(elem):
                    range_elem.remove(elem)
        elif range_id == "variant-type":
            # Keep only recommended variant types
            for elem in list(range_elem.findall("range-element")):
                if not should_include_variant_type(elem):
                    range_elem.remove(elem)
    
    # Add missing POS categories to grammatical-info range
    add_missing_pos_categories(root)
    
    # Add the special _component-lexeme relation for complex forms
    add_component_lexeme_relation(root)
    
    # Add new ranges if they don't exist
    if root.find("range[@id='complex-form-types']") is None:
        create_complex_form_types_range(root)
    if root.find("range[@id='variant-type']") is None:
        create_variant_types_range(root)
    if root.find("range[@id='usage-labels']") is None:
        create_usage_labels_range(root)
    if root.find("range[@id='recommended-traits']") is None:
        create_traits_range(root)
    
    tree.write(output_path, encoding="utf-8", xml_declaration=True)

if __name__ == "__main__":
    trim_lift_ranges(INPUT_PATH, OUTPUT_PATH)
    print(f"Trimmed LIFT ranges written to {OUTPUT_PATH}")
