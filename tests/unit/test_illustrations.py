"""
Unit tests for LIFT 0.13 Illustrations (Visual Support) - Day 33-34

Tests the illustrations attribute on Sense model for storing image references.
LIFT 0.13 spec: <illustration href="..."><label><form lang="..."><text>...</text></form></label></illustration>
"""
import pytest
from app.models.sense import Sense
from app.models.entry import Entry


class TestSenseIllustrations:
    """Test basic illustrations attribute on Sense"""
    
    def test_sense_has_illustrations_attribute(self):
        """Sense should have an illustrations attribute"""
        sense = Sense(glosses={'en': 'test'})
        assert hasattr(sense, 'illustrations')
    
    def test_sense_illustrations_defaults_to_empty_list(self):
        """Sense illustrations should default to empty list"""
        sense = Sense(glosses={'en': 'test'})
        assert sense.illustrations == []
        assert isinstance(sense.illustrations, list)
    
    def test_sense_supports_single_illustration(self):
        """Sense should support adding a single illustration"""
        illustration = {
            'href': 'images/cat.jpg',
            'label': {'en': 'Domestic cat'}
        }
        sense = Sense(
            glosses={'en': 'cat'},
            illustrations=[illustration]
        )
        assert len(sense.illustrations) == 1
        assert sense.illustrations[0]['href'] == 'images/cat.jpg'
        assert sense.illustrations[0]['label']['en'] == 'Domestic cat'
    
    def test_sense_supports_multiple_illustrations(self):
        """Sense should support multiple illustrations"""
        illustrations = [
            {'href': 'images/cat1.jpg', 'label': {'en': 'Cat sitting'}},
            {'href': 'images/cat2.jpg', 'label': {'en': 'Cat sleeping'}}
        ]
        sense = Sense(
            glosses={'en': 'cat'},
            illustrations=illustrations
        )
        assert len(sense.illustrations) == 2
        assert sense.illustrations[0]['href'] == 'images/cat1.jpg'
        assert sense.illustrations[1]['href'] == 'images/cat2.jpg'


class TestIllustrationStructure:
    """Test illustration data structure"""
    
    def test_illustration_with_href_only(self):
        """Illustration can have href without label"""
        illustration = {'href': 'images/simple.jpg'}
        sense = Sense(
            glosses={'en': 'test'},
            illustrations=[illustration]
        )
        assert sense.illustrations[0]['href'] == 'images/simple.jpg'
        assert sense.illustrations[0].get('label') is None
    
    def test_illustration_with_multilingual_labels(self):
        """Illustration labels can be multilingual"""
        illustration = {
            'href': 'images/house.jpg',
            'label': {
                'en': 'Traditional house',
                'fr': 'Maison traditionnelle',
                'es': 'Casa tradicional'
            }
        }
        sense = Sense(
            glosses={'en': 'house'},
            illustrations=[illustration]
        )
        assert sense.illustrations[0]['label']['en'] == 'Traditional house'
        assert sense.illustrations[0]['label']['fr'] == 'Maison traditionnelle'
        assert sense.illustrations[0]['label']['es'] == 'Casa tradicional'
    
    def test_illustration_supports_relative_paths(self):
        """Illustration href can be relative path"""
        illustration = {'href': 'subfolder/image.png'}
        sense = Sense(
            glosses={'en': 'test'},
            illustrations=[illustration]
        )
        assert sense.illustrations[0]['href'] == 'subfolder/image.png'
    
    def test_illustration_supports_urls(self):
        """Illustration href can be URL"""
        illustration = {'href': 'https://example.com/images/test.jpg'}
        sense = Sense(
            glosses={'en': 'test'},
            illustrations=[illustration]
        )
        assert sense.illustrations[0]['href'] == 'https://example.com/images/test.jpg'


class TestIllustrationIntegration:
    """Test illustrations integration with other sense data"""
    
    def test_sense_with_illustrations_and_other_data(self):
        """Sense can have illustrations along with other data"""
        sense = Sense(
            id_='test-sense-123',
            glosses={'en': 'cat', 'fr': 'chat'},
            definitions={'en': 'A small carnivorous mammal'},
            grammatical_info='Noun',
            illustrations=[
                {'href': 'images/cat.jpg', 'label': {'en': 'Cat'}}
            ]
        )
        assert sense.id == 'test-sense-123'
        assert sense.glosses['en'] == 'cat'
        assert sense.grammatical_info == 'Noun'
        assert len(sense.illustrations) == 1
        assert sense.illustrations[0]['href'] == 'images/cat.jpg'
    
    def test_update_illustrations(self):
        """Sense illustrations can be updated"""
        sense = Sense(
            glosses={'en': 'test'},
            illustrations=[{'href': 'old.jpg'}]
        )
        assert len(sense.illustrations) == 1
        
        sense.illustrations.append({'href': 'new.jpg', 'label': {'en': 'New image'}})
        assert len(sense.illustrations) == 2
        assert sense.illustrations[1]['href'] == 'new.jpg'
    
    def test_empty_illustrations_list(self):
        """Sense with empty illustrations list is valid"""
        sense = Sense(
            glosses={'en': 'test'},
            illustrations=[]
        )
        assert sense.illustrations == []
        assert isinstance(sense.illustrations, list)
