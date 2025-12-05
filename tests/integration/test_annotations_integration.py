"""
Integration tests for LIFT 0.13 Annotations (Day 26-27).

Tests full round-trip of annotation creation, persistence, and retrieval
for editorial workflow support (review status, comments, metadata).
"""

import pytest
from lxml import etree as ET
from app.models.entry import Entry
from app.models.sense import Sense
from app.parsers.lift_parser import LIFTParser


@pytest.mark.integration
class TestAnnotationsIntegration:
    """Integration tests for LIFT 0.13 annotation support."""

    def test_entry_level_annotation_persistence(self):
        """Test that entry-level annotations persist through save/load cycle."""
        # Create entry with annotation
        entry = Entry(
            id="test-entry-1",
            lexical_unit={"en": "test"},
            senses=[Sense(glosses={"en": "test"})],
            annotations=[{
                "name": "review-status",
                "value": "approved",
                "who": "editor@example.com",
                "when": "2024-12-01T10:00:00"
            }]
        )
        
        # Generate XML
        parser = LIFTParser()
        xml_string = parser.generate_lift_string([entry])
        
        # Verify XML contains annotation
        root = ET.fromstring(xml_string.encode('utf-8'))
        annotation = root.find('.//{http://fieldworks.sil.org/schemas/lift/0.13}annotation[@name="review-status"]')
        assert annotation is not None
        assert annotation.get('value') == "approved"
        assert annotation.get('who') == "editor@example.com"
        assert annotation.get('when') == "2024-12-01T10:00:00"
        
        # Parse back from XML
        entries = parser.parse_lift_content(xml_string)
        assert len(entries) == 1
        parsed_entry = entries[0]
        
        # Verify annotation was preserved
        assert hasattr(parsed_entry, 'annotations')
        assert len(parsed_entry.annotations) == 1
        annotation_data = parsed_entry.annotations[0]
        assert annotation_data['name'] == "review-status"
        assert annotation_data['value'] == "approved"
        assert annotation_data['who'] == "editor@example.com"
        assert annotation_data['when'] == "2024-12-01T10:00:00"

    def test_sense_level_annotation_persistence(self):
        """Test that sense-level annotations persist through save/load cycle."""
        # Create entry with sense annotation
        sense = Sense(
            id="sense-1",
            glosses={"en": "meaning"},
            examples=[],
            annotations=[{
                "name": "flagged",
                "value": "needs-revision",
                "who": "reviewer@example.com"
            }]
        )
        
        entry = Entry(
            id="test-entry-2",
            lexical_unit={"en": "test"},
            senses=[sense]
        )
        
        # Generate XML
        parser = LIFTParser()
        xml_string = parser.generate_lift_string([entry])
        
        # Verify XML contains sense annotation
        root = ET.fromstring(xml_string.encode('utf-8'))
        annotation = root.find('.//{http://fieldworks.sil.org/schemas/lift/0.13}sense/{http://fieldworks.sil.org/schemas/lift/0.13}annotation[@name="flagged"]')
        assert annotation is not None
        assert annotation.get('value') == "needs-revision"
        assert annotation.get('who') == "reviewer@example.com"
        
        # Parse back from XML
        entries = parser.parse_lift_content(xml_string)
        parsed_sense = entries[0].senses[0]
        
        # Verify annotation was preserved
        assert hasattr(parsed_sense, 'annotations')
        assert len(parsed_sense.annotations) == 1
        annotation_data = parsed_sense.annotations[0]
        assert annotation_data['name'] == "flagged"
        assert annotation_data['value'] == "needs-revision"
        assert annotation_data['who'] == "reviewer@example.com"

    def test_multiple_annotations_per_element(self):
        """Test multiple annotations on a single entry or sense."""
        # Create entry with multiple annotations
        entry = Entry(
            id="test-entry-3",
            lexical_unit={"en": "test"},
            senses=[Sense(glosses={"en": "test"})],
            annotations=[
                {
                    "name": "review-status",
                    "value": "approved"
                },
                {
                    "name": "priority",
                    "value": "high"
                },
                {
                    "name": "comment",
                    "who": "editor@example.com"
                }
            ]
        )
        
        # Generate and parse XML
        parser = LIFTParser()
        xml_string = parser.generate_lift_string([entry])
        entries = parser.parse_lift_content(xml_string)
        
        # Verify all annotations preserved
        parsed_entry = entries[0]
        assert len(parsed_entry.annotations) == 3
        
        # Check each annotation
        names = [a['name'] for a in parsed_entry.annotations]
        assert "review-status" in names
        assert "priority" in names
        assert "comment" in names

    def test_annotation_with_multitext_content(self):
        """Test annotation with multitext content (forms)."""
        # Create annotation with content
        entry = Entry(
            id="test-entry-4",
            lexical_unit={"en": "test"},
            senses=[Sense(glosses={"en": "test"})],
            annotations=[{
                "name": "reviewer-comment",
                "who": "reviewer@example.com",
                "when": "2024-12-01T14:30:00",
                "content": {
                    "en": "This entry needs more examples",
                    "fr": "Cette entrée a besoin de plus d'exemples"
                }
            }]
        )
        
        # Generate XML
        parser = LIFTParser()
        xml_string = parser.generate_lift_string([entry])
        
        # Verify XML structure
        root = ET.fromstring(xml_string.encode('utf-8'))
        annotation = root.find('.//{http://fieldworks.sil.org/schemas/lift/0.13}annotation[@name="reviewer-comment"]')
        assert annotation is not None
        
        # Check multitext forms
        forms = annotation.findall('{http://fieldworks.sil.org/schemas/lift/0.13}form')
        assert len(forms) == 2
        
        # Parse back
        entries = parser.parse_lift_content(xml_string)
        annotation_data = entries[0].annotations[0]
        
        # Verify content preserved
        assert 'content' in annotation_data
        assert annotation_data['content']['en'] == "This entry needs more examples"
        assert annotation_data['content']['fr'] == "Cette entrée a besoin de plus d'exemples"

    def test_annotation_minimal_structure(self):
        """Test annotation with only required 'name' attribute."""
        # Create annotation with only name
        entry = Entry(
            id="test-entry-5",
            lexical_unit={"en": "test"},
            senses=[Sense(glosses={"en": "test"})],
            annotations=[{
                "name": "needs-revision"
            }]
        )
        
        # Generate and parse XML
        parser = LIFTParser()
        xml_string = parser.generate_lift_string([entry])
        entries = parser.parse_lift_content(xml_string)
        
        # Verify minimal annotation preserved
        annotation_data = entries[0].annotations[0]
        assert annotation_data['name'] == "needs-revision"
        assert 'value' not in annotation_data or not annotation_data.get('value')
        assert 'who' not in annotation_data or not annotation_data.get('who')
        assert 'when' not in annotation_data or not annotation_data.get('when')

    def test_annotation_datetime_formats(self):
        """Test various datetime formats in 'when' attribute."""
        test_cases = [
            "2024-12-01T10:00:00",
            "2024-12-01T10:00:00Z",
            "2024-12-01T10:00:00+00:00",
            "2024-12-01"
        ]
        
        parser = LIFTParser()
        
        for idx, when_value in enumerate(test_cases):
            entry = Entry(
                id=f"test-entry-{idx}",
                lexical_unit={"en": "test"},
                senses=[Sense(id="s1", glosses={"en": "test"}, examples=[])],
                annotations=[{
                    "name": "review-status",
                    "when": when_value
                }]
            )
            
            # Generate and parse XML
            xml_string = parser.generate_lift_string([entry])
            entries = parser.parse_lift_content(xml_string)
            
            # Verify datetime preserved
            annotation_data = entries[0].annotations[0]
            assert annotation_data['when'] == when_value

    def test_mixed_entry_and_sense_annotations(self):
        """Test annotations at both entry and sense levels in same entry."""
        # Create entry with both entry-level and sense-level annotations
        sense = Sense(
            id="sense-1",
            glosses={"en": "meaning"},
            examples=[],
            annotations=[{
                "name": "sense-status",
                "value": "verified"
            }]
        )
        
        entry = Entry(
            id="test-entry-6",
            lexical_unit={"en": "test"},
            senses=[sense],
            annotations=[{
                "name": "entry-status",
                "value": "complete"
            }]
        )
        
        # Generate and parse XML
        parser = LIFTParser()
        xml_string = parser.generate_lift_string([entry])
        entries = parser.parse_lift_content(xml_string)
        
        # Verify both levels preserved
        parsed_entry = entries[0]
        assert len(parsed_entry.annotations) == 1
        assert parsed_entry.annotations[0]['name'] == "entry-status"
        
        parsed_sense = parsed_entry.senses[0]
        assert len(parsed_sense.annotations) == 1
        assert parsed_sense.annotations[0]['name'] == "sense-status"

    def test_annotation_common_workflow_names(self):
        """Test annotations with common editorial workflow names."""
        common_names = [
            "review-status",
            "comment",
            "reviewer-comment",
            "approval-status",
            "flagged",
            "priority",
            "needs-revision"
        ]
        
        annotations = [{"name": name, "value": f"test-{name}"} for name in common_names]
        
        entry = Entry(
            id="test-entry-7",
            lexical_unit={"en": "test"},
            senses=[Sense(glosses={"en": "test"})],
            annotations=annotations
        )
        
        # Generate and parse XML
        parser = LIFTParser()
        xml_string = parser.generate_lift_string([entry])
        entries = parser.parse_lift_content(xml_string)
        
        # Verify all common names preserved
        parsed_annotations = entries[0].annotations
        assert len(parsed_annotations) == len(common_names)
        
        for annotation in parsed_annotations:
            assert annotation['name'] in common_names
            assert annotation['value'].startswith("test-")

    def test_annotation_serialization_to_dict(self):
        """Test that annotations are included in Entry.to_dict() and Sense.to_dict()."""
        # Create entry with annotations
        sense = Sense(
            id="sense-1",
            glosses={"en": "meaning"},
            examples=[],
            annotations=[{"name": "sense-annotation"}]
        )
        
        entry = Entry(
            id="test-entry-8",
            lexical_unit={"en": "test"},
            senses=[sense],
            annotations=[{"name": "entry-annotation"}]
        )
        
        # Convert to dict
        entry_dict = entry.to_dict()
        
        # Verify annotations in dict
        assert 'annotations' in entry_dict
        assert len(entry_dict['annotations']) == 1
        assert entry_dict['annotations'][0]['name'] == "entry-annotation"
        
        # Verify sense annotations
        sense_dict = entry_dict['senses'][0]
        assert 'annotations' in sense_dict
        assert len(sense_dict['annotations']) == 1
        assert sense_dict['annotations'][0]['name'] == "sense-annotation"

    def test_empty_annotations_list(self):
        """Test that empty annotations list doesn't break XML generation."""
        # Create entry with empty annotations
        entry = Entry(
            id="test-entry-9",
            lexical_unit={"en": "test"},
            senses=[Sense(glosses={"en": "test"})],
            annotations=[]
        )
        
        # Generate XML
        parser = LIFTParser()
        xml_string = parser.generate_lift_string([entry])
        
        # Verify no annotation elements in XML
        root = ET.fromstring(xml_string.encode('utf-8'))
        annotations = root.findall('.//{http://fieldworks.sil.org/schemas/lift/0.13}annotation')
        assert len(annotations) == 0
        
        # Parse back
        entries = parser.parse_lift_content(xml_string)
        assert len(entries) == 1
        # Annotations may be empty list or not present
        if hasattr(entries[0], 'annotations'):
            assert len(entries[0].annotations) == 0
